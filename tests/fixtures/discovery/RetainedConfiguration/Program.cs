using Hoard.Hosting;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.Extensions.DependencyInjection;

var builder = new ServiceCollection().AddHoard();
await using var evaluation = await builder.EvaluateConfigurationAsync(
    new("""{"configurationversion":1,"enabledmodules":[],"metadataprovider":"missing","artifactprovider":"missing","identitymodules":[],"requiredcapabilities":[],"modules":{}}"""),
    new HoardPlatformVersions("0.1.0", "0.1.0"), new HoardLifecycleOptions());
if (evaluation.Outcome != HoardConfigurationOutcome.Failed || evaluation.Configuration is not null
    || evaluation.Report.Diagnostics.IsEmpty)
{ throw new InvalidOperationException("Retained configuration rejection failed."); }
Console.WriteLine("configuration-compatible");
