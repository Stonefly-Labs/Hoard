using System.Collections.Immutable;
using System.Text;

namespace Hoard.Hosting.Configuration;

internal static class ConfigurationSourceResolution
{
    internal static async Task<EffectiveConfiguration> InspectAsync(HoardBuilder builder, HoardConfigurationInput input,
        HoardConfigurationOptions? limits = null)
    {
        var options = limits ?? new();
        var supervisor = new ConfigurationSupervisor(options, CancellationToken.None);
        try
        {
            if (input.InputError is { } inputError)
            { supervisor.Reject(inputError, HoardConfigurationPhase.Sources, input.InputErrorSource); }
            var metadata = ConfigurationMetadata.Validate(builder, options, supervisor);
            var result = await ResolveAsync(input, metadata, options, supervisor).ConfigureAwait(false);
            supervisor.Complete(true);
            return result;
        }
        catch (ConfigurationFailure failure)
        { supervisor.Fail(failure.Rule); supervisor.Complete(false); throw; }
        finally { supervisor.Dispose(); }
    }

    internal static async Task<EffectiveConfiguration> ResolveAsync(HoardConfigurationInput input,
        ImmutableDictionary<string, ConfigurationRegistration> metadata, HoardConfigurationOptions limits,
        ConfigurationSupervisor supervisor)
    {
        var merged = new Dictionary<string, SourceAssignment>(StringComparer.Ordinal);
        async Task Parse(string text, HoardConfigurationSource source, bool overlay)
        {
            var parsed = await supervisor.RunAsync(HoardConfigurationPhase.Structure, source, "configuration",
                _ => ValueTask.FromResult(new ConfigurationParser(metadata, limits, supervisor, source).Document(text, overlay))).ConfigureAwait(false);
            foreach (var assignment in parsed) { merged[assignment.Identity] = assignment; }
        }
        await Parse(input.Defaults, HoardConfigurationSource.Defaults, false).ConfigureAwait(false);
        var file = input.ExplicitFile;
        var selectorSeen = file is not null;
        var commandLine = new List<string>();
        var bytes = 0;
        foreach (var argument in input.Arguments)
        {
            supervisor.Check();
            if (!argument.StartsWith("--hoard", StringComparison.OrdinalIgnoreCase)) { continue; }
            bytes = checked(bytes + Encoding.UTF8.GetByteCount(argument));
            if (bytes > limits.MaximumDocumentBytes)
            { supervisor.Reject(HoardConfigurationRule.InputLimit, HoardConfigurationPhase.Sources, HoardConfigurationSource.CommandLine); }
            if (argument.StartsWith("--hoard-file=", StringComparison.Ordinal))
            {
                if (selectorSeen) { supervisor.Reject(HoardConfigurationRule.DuplicateSetting, HoardConfigurationPhase.Sources, HoardConfigurationSource.CommandLine); }
                selectorSeen = true;
                file = argument["--hoard-file=".Length..];
            }
            else if (argument.StartsWith("--hoard:", StringComparison.Ordinal) && argument.Contains('='))
            { commandLine.Add(argument); }
            else { supervisor.Reject(HoardConfigurationRule.InvalidSource, HoardConfigurationPhase.Sources, HoardConfigurationSource.CommandLine); }
        }
        if (selectorSeen)
        {
            if (string.IsNullOrWhiteSpace(file))
            { supervisor.Reject(HoardConfigurationRule.SourceUnavailable, HoardConfigurationPhase.Sources, HoardConfigurationSource.File); }
            var text = await supervisor.RunAsync(HoardConfigurationPhase.Sources, HoardConfigurationSource.File, "configuration",
                async token =>
                {
                    try
                    {
                        return input.ReadFile is { } reader ? await reader(file!, token).ConfigureAwait(false)
                            : await ReadFileAsync(file!, limits.MaximumDocumentBytes, token).ConfigureAwait(false);
                    }
                    catch (Exception error) when (error is not ConfigurationFailure and not OperationCanceledException)
                    { throw new ConfigurationFailure(HoardConfigurationRule.SourceUnavailable); }
                }).ConfigureAwait(false);
            await Parse(text, HoardConfigurationSource.File, false).ConfigureAwait(false);
        }
        var environmentNames = input.Environment.Keys.Where(name => name.Equals("HOARD_CONFIG", StringComparison.OrdinalIgnoreCase)).Take(2).ToArray();
        if (environmentNames.Length > 1)
        { supervisor.Reject(HoardConfigurationRule.DuplicateSetting, HoardConfigurationPhase.Sources, HoardConfigurationSource.Environment); }
        if (environmentNames.Length == 1)
        { await Parse(input.Environment[environmentNames[0]], HoardConfigurationSource.Environment, true).ConfigureAwait(false); }
        var cli = new ConfigurationParser(metadata, limits, supervisor, HoardConfigurationSource.CommandLine);
        await supervisor.RunAsync(HoardConfigurationPhase.Structure, HoardConfigurationSource.CommandLine, "configuration", _ =>
        {
            foreach (var argument in commandLine)
            {
                supervisor.Check();
                var split = argument.IndexOf('=');
                cli.CommandLine(argument["--hoard:".Length..split], argument[(split + 1)..]);
            }
            return ValueTask.FromResult(true);
        }).ConfigureAwait(false);
        foreach (var assignment in cli.Assignments) { merged[assignment.Identity] = assignment; }
        supervisor.Check();
        return new(merged.Values);
    }

    internal static async ValueTask<string> ReadFileAsync(string path, int maximum, CancellationToken token)
    {
        await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read,
            4096, FileOptions.Asynchronous | FileOptions.SequentialScan);
        using var buffer = new MemoryStream();
        var block = new byte[Math.Min(maximum + 1, 4096)];
        while (true)
        {
            var read = await stream.ReadAsync(block.AsMemory(0, Math.Min(block.Length, maximum + 1 - (int)buffer.Length)), token).ConfigureAwait(false);
            if (read == 0) { break; }
            buffer.Write(block, 0, read);
            if (buffer.Length > maximum) { throw new ConfigurationFailure(HoardConfigurationRule.InputLimit); }
        }
        return new UTF8Encoding(false, true).GetString(buffer.GetBuffer(), 0, (int)buffer.Length);
    }
}
