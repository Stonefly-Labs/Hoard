using System.Text;

namespace Hoard.Hosting.Configuration.Conversion;

internal enum ConfigurationPublicationStage { Staged, Write, Flush, Closed, PrePublish, Published }

internal static class ConfigurationPublisher
{
    internal static bool FreshDestination(string source, string destination) =>
        !source.Equals(destination, StringComparison.Ordinal) && !File.Exists(destination)
        && !Directory.Exists(destination) && new FileInfo(destination).LinkTarget is null;

    internal static async ValueTask<bool> PublishAsync(HoardConfigurationConversionSession session,
        ConfigurationSupervisor supervisor, HoardConfigurationPublication publication,
        Func<CancellationToken, ValueTask<bool>> fresh, CancellationToken token)
    {
        publication.Begin();
        string? staging = null;
        var created = false;
        try
        {
            supervisor.Check();
            if (OperatingSystem.IsWindows() || !OperatingSystem.IsLinux() && !OperatingSystem.IsMacOS())
            { throw new ConfigurationFailure(HoardConfigurationRule.PublicationFailed); }
            var parent = Path.GetDirectoryName(session.Destination)!;
            var permissions = File.GetUnixFileMode(parent);
            if (new DirectoryInfo(parent).LinkTarget is not null
                || (permissions & (UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.GroupExecute
                    | UnixFileMode.OtherRead | UnixFileMode.OtherWrite | UnixFileMode.OtherExecute)) != 0
                || !FreshDestination(session.Source, session.Destination))
            { throw new ConfigurationFailure(HoardConfigurationRule.PublicationFailed); }
            staging = Path.Combine(parent, $".hoard-configuration-{Guid.NewGuid():N}.tmp");
            await using (var stream = new FileStream(staging, new FileStreamOptions
            {
                Mode = FileMode.CreateNew,
                Access = FileAccess.Write,
                Share = FileShare.None,
                Options = FileOptions.Asynchronous | FileOptions.WriteThrough,
                UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite
            }))
            {
                created = true;
                Stage(ConfigurationPublicationStage.Staged);
                var bytes = new UTF8Encoding(false, true).GetBytes(session.Proposal);
                var split = bytes.Length / 2;
                await stream.WriteAsync(bytes.AsMemory(0, split), token).ConfigureAwait(false);
                Stage(ConfigurationPublicationStage.Write);
                await stream.WriteAsync(bytes.AsMemory(split), token).ConfigureAwait(false);
                await stream.FlushAsync(token).ConfigureAwait(false);
                stream.Flush(true);
                Stage(ConfigurationPublicationStage.Flush);
            }
            Stage(ConfigurationPublicationStage.Closed);
            supervisor.Check();
            Stage(ConfigurationPublicationStage.PrePublish);
            if (!await fresh(token).ConfigureAwait(false))
            { throw new ConfigurationFailure(HoardConfigurationRule.ConversionRejected); }
            supervisor.Check();
            File.Move(staging, session.Destination, overwrite: false);
            publication.Commit();
            Stage(ConfigurationPublicationStage.Published);
            return true;
        }
        catch (Exception error) when (error is not ConfigurationFailure and not OperationCanceledException)
        { throw new ConfigurationFailure(HoardConfigurationRule.PublicationFailed); }
        finally
        {
            publication.Finish();
            if (created) { File.Delete(staging!); }
        }

        void Stage(ConfigurationPublicationStage stage)
        {
            session.PublicationObserver?.Invoke(stage);
            ConfigurationSupervisor.PublicationEvent(stage.ToString());
        }
    }
}
