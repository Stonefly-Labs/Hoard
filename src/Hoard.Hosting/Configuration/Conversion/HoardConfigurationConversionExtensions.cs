using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Lifecycle;

namespace Hoard.Hosting.Configuration.Conversion;

public static class HoardConfigurationConversionExtensions
{
    public static async Task<HoardConfigurationConversionPreview> PreviewConfigurationConversionAsync(this HoardBuilder builder,
        string sourcePath, string destinationPath, HoardPlatformVersions platformVersions, HoardLifecycleOptions lifecycleOptions,
        HoardConfigurationOptions? configurationOptions = null, HoardEnvironmentReader? readEnvironment = null,
        HoardConfigurationFileReader? readSecretFile = null, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(platformVersions);
        ArgumentNullException.ThrowIfNull(lifecycleOptions);
        var options = configurationOptions ?? new();
        var supervisor = new ConfigurationSupervisor(options.IsValid ? options : new(), cancellationToken);
        HoardConfigurationConversionSession? session = null;
        try
        {
            if (!options.IsValid) { supervisor.Reject(HoardConfigurationRule.InvalidBudget, HoardConfigurationPhase.Conversion); }
            var paths = await supervisor.RunAsync(HoardConfigurationPhase.Conversion, HoardConfigurationSource.File,
                "configuration", _ =>
                {
                    var source = Path.GetFullPath(sourcePath);
                    var destination = Path.GetFullPath(destinationPath);
                    if (!ConfigurationPublisher.FreshDestination(source, destination))
                    { throw new ConfigurationFailure(HoardConfigurationRule.ConversionRejected); }
                    return ValueTask.FromResult((Source: source, Destination: destination));
                }).ConfigureAwait(false);
            var original = await supervisor.RunAsync(HoardConfigurationPhase.Conversion, HoardConfigurationSource.File, "configuration",
                token => ConfigurationSourceResolution.ReadFileAsync(paths.Source, options.MaximumDocumentBytes, token)).ConfigureAwait(false);
            var proposal = await supervisor.RunAsync(HoardConfigurationPhase.Conversion, HoardConfigurationSource.File, "configuration",
                _ => ValueTask.FromResult(FixtureV0Mapping.Convert(original, options))).ConfigureAwait(false);
            var data = await ConfigurationEvaluator.RunAsync(builder, new(proposal), platformVersions, lifecycleOptions,
                options, supervisor, publicOnly: true).ConfigureAwait(false);
            supervisor.Complete(true);
            session = new(builder, paths.Source, paths.Destination, Digest(original), proposal, platformVersions with { },
                lifecycleOptions with { }, options with { }, data.Composition.ServiceSnapshot, readEnvironment, readSecretFile);
        }
        catch (ConfigurationFailure failure) { supervisor.Fail(failure.Rule); }
        if (session is null) { supervisor.Complete(false); }
        ImmutableArray<HoardConfigurationChange> changes = session is null ? [] :
            [new("configurationversion", HoardConfigurationChangeKind.VersionChanged),
             .. FixtureV0Mapping.Roots.Select(pair => new HoardConfigurationChange(pair.Current,
                 pair.Current == "modules" ? HoardConfigurationChangeKind.Changed : HoardConfigurationChangeKind.SelectionChanged))];
        return new(supervisor, session, changes);
    }

    public static async Task<HoardConfigurationConversionApplyResult> ApplyConfigurationConversionAsync(this HoardBuilder builder,
        HoardConfigurationConversionSession session, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(builder);
        ArgumentNullException.ThrowIfNull(session);
        var supervisor = new ConfigurationSupervisor(session.Options, cancellationToken);
        var publication = new HoardConfigurationPublication();
        try
        {
            supervisor.Check();
            if (!session.Consume(builder))
            { supervisor.Reject(HoardConfigurationRule.ConversionRejected, HoardConfigurationPhase.Conversion); }
            if (!await supervisor.RunAsync(HoardConfigurationPhase.Conversion, HoardConfigurationSource.File,
                "configuration", Fresh).ConfigureAwait(false))
            { supervisor.Reject(HoardConfigurationRule.ConversionRejected, HoardConfigurationPhase.Conversion); }
            await ConfigurationEvaluator.RunAsync(builder, new(session.Proposal,
                readFile: session.ReadSecretFile, readEnvironment: session.ReadEnvironment),
                session.Versions, session.LifecycleOptions, session.Options, supervisor).ConfigureAwait(false);
            await supervisor.RunAsync(HoardConfigurationPhase.Publication, HoardConfigurationSource.File, "configuration",
                token => ConfigurationPublisher.PublishAsync(session, supervisor, publication, Fresh, token)).ConfigureAwait(false);
            supervisor.Complete(true);
        }
        catch (ConfigurationFailure failure) { supervisor.Fail(failure.Rule); supervisor.Complete(false); }
        var status = publication.Status;
        var outcome = status == HoardConfigurationPublicationStatus.Published ? HoardConfigurationApplyOutcome.Published
            : status == HoardConfigurationPublicationStatus.Pending ? HoardConfigurationApplyOutcome.PublicationPending
            : supervisor.Outcome == HoardConfigurationOutcome.Cancelled ? HoardConfigurationApplyOutcome.Cancelled
            : supervisor.Outcome == HoardConfigurationOutcome.TimedOut ? HoardConfigurationApplyOutcome.TimedOut
            : HoardConfigurationApplyOutcome.Rejected;
        return new(outcome, supervisor, publication);

        async ValueTask<bool> Fresh(CancellationToken token)
        {
            if (!builder.Services.SequenceEqual(session.Services)
                || !ConfigurationPublisher.FreshDestination(session.Source, session.Destination)) { return false; }
            var current = await ConfigurationSourceResolution.ReadFileAsync(session.Source,
                session.Options.MaximumDocumentBytes, token).ConfigureAwait(false);
            return CryptographicOperations.FixedTimeEquals(Digest(current), session.Digest);
        }
    }

    private static byte[] Digest(string value) => SHA256.HashData(new UTF8Encoding(false, true).GetBytes(value));
}
