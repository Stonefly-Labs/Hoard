using System.Net;
using System.Text.Json;
using Hoard.Abstractions.Modules;
using Hoard.Fixtures.Conformance.Host;
using Hoard.Hosting.Composition;
using Hoard.Hosting.Configuration;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Xunit.Abstractions;
#if CONFORMANCE_PROVIDER_PACKAGES
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Fixtures.Artifacts.HostAdapters;
using Hoard.Fixtures.Artifacts.Local;
using Hoard.Fixtures.Metadata.Hosting;
using Hoard.Testing.Conformance.Evidence;
#endif
using static Hoard.Fixtures.Conformance.Host.CompositionFixtures;

namespace Hoard.Composition.Tests;

public sealed class ConformanceMatrixTests(ITestOutputHelper output)
{
    private sealed class OwnershipObservation
    {
        private readonly Action<string, HoardServiceComposition>? write;

        public OwnershipObservation(ITestOutputHelper output, string identity, Registry registry,
            OwnershipFixtures.ControlledCallback callback)
        {
#if CONFORMANCE_PROVIDER_PACKAGES
            var owner = ConformanceOriginalObservationOutput.WriteIfRequested(
                output, identity, "none", "original-owner", null, null, ("owner", registry));
            if (owner is null) { return; }
            write = (stage, lease) =>
            {
                var probe = registry.Probes["artifact"];
                ConformanceCompositionObservationOutput.Write(output, owner, stage,
                    new Dictionary<string, int>(StringComparer.Ordinal)
                    {
                        ["callbackSettled"] = callback.Settled.IsCompleted ? 1 : 0,
                        ["workCompleted"] = callback.Work?.IsCompleted == true ? 1 : 0,
                        ["workFaulted"] = callback.Work?.IsFaulted == true ? 1 : 0,
                        ["ready"] = lease.Lifecycle.Snapshot.Ready ? 1 : 0,
                        ["admission"] = lease.Lifecycle.Snapshot.StartupAdmission ? 1 : 0,
                        ["unsafeActivities"] = lease.StopResult?.UnsafeActivities.Length ?? 0,
                        ["rootDisposal"] = (int?)(lease.StopResult?.RootDisposal) ?? 6, // No stop result; Completed is zero.
                        ["stopComplete"] = lease.StopResult?.Complete == true ? 1 : 0,
                        ["initializations"] = probe.Initializations,
                        ["assessments"] = probe.Assessments,
                        ["workers"] = probe.Workers,
                        ["stops"] = probe.Stops,
                        ["disposals"] = probe.Disposals
                    });
            };
#else
            write = null;
#endif
        }

        public bool Write(string stage, HoardServiceComposition lease)
        {
            if (write is null) { return false; }
            write(stage, lease);
            return true;
        }
    }

    private void Observe(string key, Registry registry, HoardServiceComposition? lease = null)
    {
        foreach (var (id, probe) in registry.Probes)
        {
            output.WriteLine($"{key}/{id}: constructors={probe.Constructors}; services={probe.Services}; maps={probe.Maps}; " +
                $"requests={probe.Requests}; connections={probe.Connections}; initializations={probe.Initializations}; " +
                $"assessments={probe.Assessments}; workers={probe.Workers}; stops={probe.Stops}; disposals={probe.Disposals}");
        }
        if (lease is not null)
        {
            output.WriteLine($"{key}: ready={(lease.Lifecycle.Snapshot.Ready ? 1 : 0)}; " +
                $"admission={(lease.Lifecycle.Snapshot.StartupAdmission ? 1 : 0)}; " +
                $"unsafe={lease.StopResult?.UnsafeActivities.Length ?? 0}; complete={(lease.StopResult?.Complete == true ? 1 : 0)}");
        }
    }

    private static int Effects(Probe probe) =>
        probe.Constructors + probe.Services + probe.Maps + probe.Requests + probe.Connections
        + probe.Initializations + probe.Assessments + probe.Workers + probe.Stops + probe.Disposals;

    private sealed class MatrixObservation
    {
        private readonly Action<string, HoardValidatedComposition?, Running?, int>? write;

        public MatrixObservation(ITestOutputHelper output, string identity, Registry registry)
        {
#if CONFORMANCE_PROVIDER_PACKAGES
            var owner = ConformanceOriginalObservationOutput.WriteIfRequested(
                output, identity, "none", "original-owner", null, null, ("owner", registry));
            if (owner is null) { return; }
            write = (stage, composition, running, ruleCount) =>
            {
                var probes = registry.Probes.Values;
                var lease = running?.Lease;
                ConformanceCompositionObservationOutput.Write(output, owner, stage,
                    new Dictionary<string, int>(StringComparer.Ordinal)
                    {
                        ["constructors"] = probes.Sum(probe => probe.Constructors),
                        ["services"] = probes.Sum(probe => probe.Services),
                        ["maps"] = probes.Sum(probe => probe.Maps),
                        ["requests"] = probes.Sum(probe => probe.Requests),
                        ["connections"] = probes.Sum(probe => probe.Connections),
                        ["initializations"] = probes.Sum(probe => probe.Initializations),
                        ["assessments"] = probes.Sum(probe => probe.Assessments),
                        ["workers"] = probes.Sum(probe => probe.Workers),
                        ["stops"] = probes.Sum(probe => probe.Stops),
                        ["disposals"] = probes.Sum(probe => probe.Disposals),
                        ["disabledEffects"] = registry.Probes.Where(pair =>
                            composition?.EnabledModuleIds.Contains(pair.Key) != true).Sum(pair => Effects(pair.Value)),
                        ["ready"] = lease?.Lifecycle.Snapshot.Ready == true ? 1 : 0,
                        ["admission"] = lease?.Lifecycle.Snapshot.StartupAdmission == true ? 1 : 0,
                        ["stopComplete"] = lease?.StopResult?.Complete == true ? 1 : 0,
                        ["rootDisposal"] = (int?)(lease?.StopResult?.RootDisposal) ?? 6,
                        ["unsafeActivities"] = lease?.StopResult?.UnsafeActivities.Length ?? 0,
                        ["ruleCount"] = ruleCount,
                        ["activeEdges"] = composition?.ActiveEdges.Length ?? 0,
                        ["satisfiedCapabilities"] = composition?.SatisfiedCapabilities.Length ?? 0,
                        ["publishedRoutes"] = running is null ? 0
                            : ((Microsoft.AspNetCore.Routing.IEndpointRouteBuilder)running.App)
                                .DataSources.Sum(source => source.Endpoints.Count)
                    });
            };
#else
            write = null;
#endif
        }

        public bool Write(string stage, HoardValidatedComposition? composition = null, Running? running = null,
            int ruleCount = 0)
        {
            if (write is null) { return false; }
            write(stage, composition, running, ruleCount);
            return true;
        }
    }

    private sealed class RestartObservation
    {
        private readonly Action<string, HoardServiceComposition, bool, bool, Task?>? write;

        public RestartObservation(ITestOutputHelper output, string identity, Registry registry, Probe[] inactive,
            OwnershipFixtures.ControlledCallback? callback = null)
        {
#if CONFORMANCE_PROVIDER_PACKAGES
            var owner = ConformanceOriginalObservationOutput.WriteIfRequested(
                output, identity, "none", "original-owner", null, null, ("owner", registry));
            if (owner is null) { return; }
            write = (stage, lease, configurationFixed, identityChanged, request) =>
                ConformanceCompositionObservationOutput.Write(output, owner, stage,
                    new Dictionary<string, int>(StringComparer.Ordinal)
                    {
                        ["ready"] = lease.Lifecycle.Snapshot.Ready ? 1 : 0,
                        ["admission"] = lease.Lifecycle.Snapshot.StartupAdmission ? 1 : 0,
                        ["stopComplete"] = lease.StopResult?.Complete == true ? 1 : 0,
                        ["rootDisposal"] = (int?)(lease.StopResult?.RootDisposal) ?? 6,
                        ["unsafeActivities"] = lease.StopResult?.UnsafeActivities.Length ?? 0,
                        ["workers"] = registry.Probes.Values.Sum(probe => probe.Workers),
                        ["inactiveEffects"] = inactive.Sum(Effects),
                        ["requests"] = registry.Probes.Values.Sum(probe => probe.Requests),
                        ["requestPending"] = request is { IsCompleted: false } ? 1 : 0,
                        ["requestSettled"] = request is { IsCompletedSuccessfully: true }
                            && callback?.Work?.IsCompletedSuccessfully == true && callback.Settled.IsCompleted ? 1 : 0,
                        ["configurationFixed"] = configurationFixed ? 1 : 0,
                        ["identityChanged"] = identityChanged ? 1 : 0
                    });
#else
            write = null;
#endif
        }

        public bool Write(string stage, HoardServiceComposition lease, bool configurationFixed,
            bool identityChanged, Task? request = null)
        {
            if (write is null) { return false; }
            write(stage, lease, configurationFixed, identityChanged, request);
            return true;
        }
    }

    private static void Inactive(Probe probe)
    {
        Assert.Equal(0, probe.Constructors);
        Assert.Equal(0, probe.Services);
        Assert.Equal(0, probe.Maps);
        Assert.Equal(0, probe.Requests);
        Assert.Equal(0, probe.Connections);
        Assert.Equal(0, probe.Initializations);
        Assert.Equal(0, probe.Assessments);
        Assert.Equal(0, probe.Workers);
        Assert.Equal(0, probe.Stops);
        Assert.Equal(0, probe.Disposals);
    }

    private static void Safe(IEnumerable<HoardLifecycleDiagnostic> diagnostics)
    {
        LifecycleFixtures.AssertSafe(diagnostics);
        Assert.DoesNotContain("conformance-secret", JsonSerializer.Serialize(diagnostics));
    }

    private static void SafeFailure(LifecycleTestHarness logs, params object?[] observations)
    {
        var text = string.Join("\n", logs.Logs) + JsonSerializer.Serialize(observations);
        foreach (var canary in new[] { "conformance-secret", "seeded-secret", "unsafe.example", "/private/conformance" })
        { Assert.DoesNotContain(canary, text); }
    }

    public static IEnumerable<object[]> Rejections()
    {
        yield return ["CP-04", "duplicate", "DuplicateModule"];
        yield return ["CP-05", "unknown", "UnknownSelection"];
        yield return ["CP-06", "missing-required", "MissingDependency"];
        yield return ["CP-07", "cycle-forward", "DependencyCycle"];
        yield return ["CP-07", "cycle-reordered", "DependencyCycle"];
        yield return ["CP-08", "missing-capability", "UnsupportedCapability"];
        yield return ["CP-09", "metadata-zero", "InvalidCardinality"];
        yield return ["CP-09", "metadata-two", "InvalidCardinality"];
        yield return ["CP-10", "artifact-zero", "InvalidCardinality"];
        yield return ["CP-10", "artifact-two", "InvalidCardinality"];
        yield return ["endpoint-declaration", "malformed-endpoint-enabled", "MalformedRegistry"];
        yield return ["endpoint-declaration", "malformed-endpoint-disabled", "MalformedRegistry"];
        yield return ["endpoint-declaration", "duplicate-endpoint-enabled", "MalformedRegistry"];
        yield return ["endpoint-declaration", "duplicate-endpoint-disabled", "MalformedRegistry"];
        yield return ["CP-13", "optional-incompatible", "UnsupportedDependency"];
    }

    private static (Registry Registry, HoardStartupSelection Selection) DeclarationCase(string variant, bool repaired)
    {
        var registry = new Registry();
        var selection = Selection();
        switch (variant)
        {
            case "duplicate":
                registry.Probes["metadata-other"] = Add<MetadataOther>(registry.Builder,
                    Declaration(repaired ? "metadata-other" : "metadata", ModuleCategory.Metadata));
                break;
            case "unknown":
                selection = repaired ? selection : Selection("unknown");
                break;
            case "missing-required":
                registry.Replace("metadata", declaration => declaration with { Dependencies = [Dependency("protocol")] });
                if (repaired) { registry.Protocol(); selection = Selection("protocol"); }
                break;
            case "cycle-forward":
            case "cycle-reordered":
                registry.Replace("metadata", declaration => declaration with { Dependencies = [Dependency("artifact")] });
                registry.Replace("artifact", declaration => declaration with
                { Dependencies = repaired ? [] : [Dependency("metadata")] });
                if (variant == "cycle-reordered") { registry.Replace("metadata", declaration => declaration); }
                break;
            case "missing-capability":
                selection = selection with { RequiredCapabilities = [new("artifact", "feature", "[0.1.0]", false)] };
                if (repaired)
                {
                    registry.Replace("artifact", declaration => declaration with
                    { Capabilities = [new() { Id = "feature", Version = "0.1.0", Description = "Required fixture guarantee." }] });
                }
                break;
            case "metadata-zero":
                selection = repaired ? selection : selection with { EnabledModuleIds = ["artifact"] };
                break;
            case "artifact-zero":
                selection = repaired ? selection : selection with { EnabledModuleIds = ["metadata"] };
                break;
            case "metadata-two":
                registry.Probes["metadata-other"] = Add<MetadataOther>(registry.Builder, Declaration("metadata-other", ModuleCategory.Metadata));
                if (!repaired) { selection = Selection("metadata-other"); }
                break;
            case "artifact-two":
                registry.Probes["artifact-other"] = Add<ArtifactOther>(registry.Builder, Declaration("artifact-other", ModuleCategory.Artifact));
                if (!repaired) { selection = Selection("artifact-other"); }
                break;
            case "optional-incompatible":
                registry.Replace("metadata", declaration => declaration with { Dependencies = [Dependency("protocol", true)] });
                registry.Protocol(Declaration("protocol", ModuleCategory.Protocol) with { Version = repaired ? "0.1.0" : "9.0.0" });
                selection = Selection("protocol");
                break;
            case "malformed-endpoint-enabled":
            case "malformed-endpoint-disabled":
            case "duplicate-endpoint-enabled":
            case "duplicate-endpoint-disabled":
                var endpoint = Declaration("protocol", ModuleCategory.Protocol);
                if (!repaired)
                {
                    endpoint = endpoint with
                    {
                        Endpoints = variant.StartsWith("malformed-", StringComparison.Ordinal)
                            ? [new() { Id = "protocol/probe", Description = "Malformed declared responsibility identifier." }]
                            : [.. endpoint.Endpoints, endpoint.Endpoints[0]]
                    };
                }
                registry.Protocol(endpoint);
                if (variant.EndsWith("-enabled", StringComparison.Ordinal)) { selection = Selection("protocol"); }
                break;
            default: throw new ArgumentOutOfRangeException(nameof(variant));
        }
        return (registry, selection);
    }

    [Theory]
    [MemberData(nameof(Rejections))]
    public async Task Declaration_rejection_and_single_input_repair(string id, string variant, string rule)
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(Declaration_rejection_and_single_input_repair)}(id: \"{id}\", variant: \"{variant}\", rule: \"{rule}\")";
        var (invalid, badSelection) = DeclarationCase(variant, false);
        var rejectedObservation = new MatrixObservation(output, identity, invalid);
        var rejected = invalid.Validate(badSelection);
        Assert.Null(rejected.Composition);
        Assert.Contains(rejected.Diagnostics, item => item.RuleCode == rule);
        if (id == "CP-11")
        {
            var diagnostic = Assert.Single(rejected.Diagnostics);
            Assert.Equal("protocol", diagnostic.ModuleId);
            Assert.Equal(HoardLifecyclePhase.Validating, diagnostic.Phase);
        }
        Safe(rejected.Diagnostics);
        Assert.All(invalid.Probes.Values, Inactive);
        if (!rejectedObservation.Write("declaration-rejected",
            ruleCount: rejected.Diagnostics.Count(item => item.RuleCode == rule)))
        { Observe($"{id}/{variant}/rejection", invalid); }

        var (valid, goodSelection) = DeclarationCase(variant, true);
        var repairedObservation = new MatrixObservation(output, identity, valid);
        var accepted = valid.Validate(goodSelection);
        Assert.NotNull(accepted.Composition);
        Assert.Empty(accepted.Diagnostics);
        if (variant == "optional-incompatible")
        { Assert.Single(accepted.Composition.ActiveEdges, edge => edge.Optional && edge.PrerequisiteId == "protocol"); }
        await using var running = await valid.BuildAsync(accepted.Composition);
        await running.StartAsync();
        Assert.True(running.Lease.Lifecycle.Snapshot.Ready);
        using var client = running.App.GetTestClient();
        Assert.Equal("conformance", await client.GetStringAsync("/metadata"));
        await LifecycleTestHarness.Until(() => accepted.Composition.EnabledModuleIds.All(module => valid.Probes[module].Workers == 1));
        repairedObservation.Write("declaration-ready", accepted.Composition, running);
        await running.App.StopHoardApplicationAsync(running.Lease);
        await running.DisposeAsync();
        Assert.True(running.Lease.StopResult!.Complete);
        foreach (var (module, probe) in valid.Probes)
        {
            if (!accepted.Composition.EnabledModuleIds.Contains(module)) { Inactive(probe); continue; }
            Assert.Equal(1, probe.Constructors);
            Assert.Equal(1, probe.Services);
            Assert.Equal(1, probe.Maps);
            Assert.Equal(1, probe.Initializations);
            Assert.Equal(1, probe.Assessments);
            Assert.Equal(1, probe.Connections);
            Assert.Equal(1, probe.Workers);
            Assert.Equal(1, probe.Stops);
            Assert.Equal(1, probe.Disposals);
        }
        if (!repairedObservation.Write("declaration-stopped", accepted.Composition, running))
        { Observe($"{id}/{variant}/repair", valid, running.Lease); }
    }

    [Fact]
    public async Task CP03_explicit_multiple_protocols_and_identity_schemes_start_and_stop()
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP03_explicit_multiple_protocols_and_identity_schemes_start_and_stop)}";
        var registry = new Registry();
        registry.Protocol();
        registry.Probes["protocol-other"] = Add<ProtocolOther>(registry.Builder, Declaration("protocol-other", ModuleCategory.Protocol));
        registry.Probes["identity"] = Add<Identity>(registry.Builder, Declaration("identity", ModuleCategory.Identity));
        registry.Probes["identity-other"] = Add<IdentityOther>(registry.Builder, Declaration("identity-other", ModuleCategory.Identity));
        var observation = new MatrixObservation(output, identity, registry);
        var composition = registry.Validate(Selection("protocol", "protocol-other", "identity", "identity-other")).Composition;
        Assert.NotNull(composition);
        Assert.Equal(6, composition.EnabledModuleIds.Length);
        Assert.Equal("metadata", composition.MetadataModuleId);
        Assert.Equal("artifact", composition.ArtifactModuleId);
        await using var running = await registry.BuildAsync(composition);
        await running.StartAsync();
        using var client = running.App.GetTestClient();
        foreach (var id in composition.EnabledModuleIds) { Assert.Equal("conformance", await client.GetStringAsync("/" + id)); }
        await LifecycleTestHarness.Until(() => registry.Probes.Values.All(probe => probe.Workers == 1));
        observation.Write("multiple-ready", composition, running);
        await running.DisposeAsync();
        Assert.True(running.Lease.StopResult!.Complete);
        Assert.All(registry.Probes.Values, probe =>
        {
            Assert.Equal(1, probe.Constructors);
            Assert.Equal(1, probe.Services);
            Assert.Equal(1, probe.Maps);
            Assert.Equal(1, probe.Requests);
            Assert.Equal(1, probe.Initializations);
            Assert.Equal(1, probe.Assessments);
            Assert.Equal(1, probe.Connections);
            Assert.Equal(1, probe.Workers);
            Assert.Equal(1, probe.Stops);
            Assert.Equal(1, probe.Disposals);
        });
        if (!observation.Write("multiple-stopped", composition, running))
        { Observe("CP-03/multiplicity", registry, running.Lease); }
    }

    [Fact]
    public async Task Declared_endpoint_ids_preserve_owner_scope_and_do_not_infer_route_namespaces()
    {
        var registry = new Registry();
        var protocol = registry.Protocol(Declaration("protocol", ModuleCategory.Protocol) with
        {
            Endpoints =
            [
                new() { Id = "probe", Description = "An identifier shared by distinct module owners." },
                new() { Id = "probe.catalog", Description = "A distinct identifier, not an overlapping route namespace." }
            ]
        });
        protocol.Map = endpoints =>
        {
            foreach (var (responsibility, path) in new[] { ("probe", "/protocol"), ("probe.catalog", "/protocol/catalog") })
            {
                endpoints.Map(responsibility, path, ["GET"], async context =>
                {
                    Interlocked.Increment(ref protocol.Requests);
                    await context.Response.WriteAsync("conformance");
                });
            }
        };
        var accepted = registry.Validate(Selection("protocol"));
        Assert.NotNull(accepted.Composition);
        Assert.Empty(accepted.Diagnostics);
        Assert.All(registry.Probes.Values, Inactive);
        await using var running = await registry.BuildAsync(accepted.Composition);
        await running.StartAsync();
        Assert.True(running.Lease.Lifecycle.Snapshot.Ready);
        using var client = running.App.GetTestClient();
        foreach (var path in new[] { "/metadata", "/artifact", "/protocol", "/protocol/catalog" })
        { Assert.Equal("conformance", await client.GetStringAsync(path)); }
        Assert.Equal(2, protocol.Requests);
        await running.DisposeAsync();
        Assert.True(running.Lease.StopResult!.Complete);
        Assert.All(registry.Probes.Values, probe => Assert.Equal(1, probe.Disposals));
        Observe("declared-endpoint-scopes/permitted", registry, running.Lease);
    }

    [Fact]
    public async Task CP11_actual_route_ambiguity_rejects_before_publication_and_repair_starts()
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP11_actual_route_ambiguity_rejects_before_publication_and_repair_starts)}";
        foreach (var repaired in new[] { false, true })
        {
            var registry = new Registry();
            var observation = new MatrixObservation(output, identity, registry);
            var ruleCount = 0;
            var protocol = registry.Protocol();
            protocol.Path = repaired ? "/protocol" : "/metadata";
            var validated = registry.Validate(Selection("protocol"));
            Assert.NotNull(validated.Composition);
            await using var running = await registry.BuildAsync(validated.Composition);
            if (repaired)
            {
                await running.StartAsync();
                using var client = running.App.GetTestClient();
                Assert.Equal("conformance", await client.GetStringAsync("/metadata"));
                Assert.Equal("conformance", await client.GetStringAsync("/protocol"));
                Assert.True(running.Lease.Lifecycle.Snapshot.Ready);
                await LifecycleTestHarness.Until(() => registry.Probes.Values.All(probe => probe.Workers == 1));
                observation.Write("mapping-ready", validated.Composition, running);
            }
            else
            {
                var failure = await Assert.ThrowsAsync<HoardLifecycleException>(() => running.App.MapHoardModulesAsync(running.Lease));
                Assert.Contains(failure.Diagnostics, item => item.RuleCode == "AmbiguousRoute");
                ruleCount = failure.Diagnostics.Count(item => item.RuleCode == "AmbiguousRoute");
                Safe(failure.Diagnostics);
                Assert.False(running.Lease.Lifecycle.Snapshot.Ready);
                Assert.False(running.Lease.Lifecycle.Snapshot.StartupAdmission);
                Assert.Empty(((Microsoft.AspNetCore.Routing.IEndpointRouteBuilder)running.App).DataSources);
                Assert.All(registry.Probes.Values, probe =>
                {
                    Assert.Equal(1, probe.Constructors);
                    Assert.Equal(1, probe.Maps);
                    Assert.Equal(0, probe.Initializations);
                    Assert.Equal(0, probe.Assessments);
                    Assert.Equal(0, probe.Requests);
                    Assert.Equal(0, probe.Connections);
                    Assert.Equal(0, probe.Workers);
                });
                observation.Write("mapping-rejected", validated.Composition, running, ruleCount);
            }
            await running.DisposeAsync();
            Assert.True(running.Lease.StopResult!.Complete);
            if (!observation.Write(repaired ? "mapping-stopped" : "mapping-denial-stopped",
                validated.Composition, running, ruleCount))
            { Observe($"CP-11/route-conflict.{(repaired ? "repair" : "reject")}", registry, running.Lease); }
        }
    }

    [Theory]
    [InlineData("absent")]
    [InlineData("registered-disabled")]
    [InlineData("enabled-compatible")]
    [InlineData("enabled-incompatible")]
    public async Task CP12_CP13_optional_target_policy_is_unchanged_by_selection(string target)
    {
        foreach (var repaired in target == "enabled-incompatible" ? new[] { false, true } : new[] { false })
        {
            var registry = new Registry();
            registry.Replace("metadata", declaration => declaration with { Dependencies = [Dependency("protocol", true)] });
            var enabled = target.StartsWith("enabled-", StringComparison.Ordinal);
            if (target != "absent")
            {
                registry.Protocol(Declaration("protocol", ModuleCategory.Protocol) with
                {
                    Version = target == "enabled-incompatible" && !repaired ? "9.0.0" : "0.1.0",
                    Capabilities = [new() { Id = "integration", Version = "0.1.0", Description = "Enabled optional integration." }]
                });
            }
            var selection = enabled ? Selection("protocol") : Selection();
            var validation = registry.Validate(selection);
            Assert.All(registry.Probes.Values, Inactive);
            if (target == "enabled-incompatible" && !repaired)
            {
                Assert.Null(validation.Composition);
                Assert.Contains(validation.Diagnostics, diagnostic => diagnostic.RuleCode == "UnsupportedDependency");
                Safe(validation.Diagnostics);
                Observe($"CP-13/{target}/rejected", registry);
                continue;
            }
            var composition = validation.Composition;
            Assert.NotNull(composition);
            Assert.Empty(validation.Diagnostics);
            Assert.Equal(enabled ? 1 : 0, composition.ActiveEdges.Length);
            if (enabled)
            {
                var edge = Assert.Single(composition.ActiveEdges);
                Assert.True(edge.Optional);
                Assert.Equal("protocol", edge.PrerequisiteId);
                Assert.Equal("metadata", edge.DependentId);
                Assert.Equal("[0.1.0,0.2.0)", edge.VersionRange);
            }
            var demand = registry.Validate(selection with
            { RequiredCapabilities = [new("protocol", "integration", "[0.1.0]", false)] });
            Assert.Equal(enabled, demand.Composition is not null);
            if (enabled) { Assert.Single(demand.Composition!.SatisfiedCapabilities); }
            else
            {
                Assert.Empty(composition.SatisfiedCapabilities);
                Assert.Contains(demand.Diagnostics, diagnostic => diagnostic.RuleCode == "UnsupportedCapability");
                Safe(demand.Diagnostics);
            }
            await using var running = await registry.BuildAsync(composition);
            await running.StartAsync();
            Assert.True(running.Lease.Lifecycle.Snapshot.StartupAdmission);
            Assert.True(running.Lease.Lifecycle.Snapshot.Ready);
            using var client = running.App.GetTestClient();
            using var response = await client.GetAsync("/protocol");
            Assert.Equal(enabled ? HttpStatusCode.OK : HttpStatusCode.NotFound, response.StatusCode);
            await LifecycleTestHarness.Until(() => composition.EnabledModuleIds.All(id => registry.Probes[id].Workers == 1));
            await running.DisposeAsync();
            Assert.True(running.Lease.StopResult!.Complete);
            if (enabled)
            {
                var probe = registry.Probes["protocol"];
                Assert.Equal(1, probe.Constructors);
                Assert.Equal(1, probe.Maps);
                Assert.Equal(1, probe.Requests);
                Assert.Equal(1, probe.Connections);
                Assert.Equal(1, probe.Workers);
                Assert.Equal(1, probe.Disposals);
            }
            else if (target == "registered-disabled") { Inactive(registry.Probes["protocol"]); }
            Observe($"CP-12-13/{target}/repaired-{repaired}", registry, running.Lease);
        }
    }

    [Theory]
    [InlineData("absent")]
    [InlineData("registered-disabled")]
    public async Task CP12_disabled_effects_and_unavailable_optional_integration(string target)
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP12_disabled_effects_and_unavailable_optional_integration)}(target: \"{target}\")";
        var registry = new Registry();
        var disabled = registry.Protocol();
        registry.Replace("metadata", declaration => declaration with { Dependencies = [Dependency("identity", true)] });
        if (target == "registered-disabled")
        {
            registry.Probes["identity"] = Add<Identity>(registry.Builder,
                Declaration("identity", ModuleCategory.Identity) with
                {
                    Version = "9.0.0",
                    Capabilities = [new() { Id = "integration", Version = "0.1.0", Description = "Only enabled targets supply this." }]
                });
        }
        var observation = new MatrixObservation(output, identity, registry);
        var validated = registry.Validate();
        Assert.NotNull(validated.Composition);
        Assert.Empty(validated.Composition.ActiveEdges);
        Assert.Empty(validated.Composition.SatisfiedCapabilities);
        var demanded = registry.Validate(Selection() with
        { RequiredCapabilities = [new("identity", "integration", "[0.1.0]", false)] });
        Assert.Null(demanded.Composition);
        Assert.Contains(demanded.Diagnostics, diagnostic => diagnostic.RuleCode == "UnsupportedCapability");
        Safe(demanded.Diagnostics);
        await using var running = await registry.BuildAsync(validated.Composition);
        await running.StartAsync();
        using var client = running.App.GetTestClient();
        using var response = await client.GetAsync("/protocol");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Inactive(disabled);
        if (target == "registered-disabled") { Inactive(registry.Probes["identity"]); }
        Assert.Equal(HoardModuleStatus.Disabled, Assert.Single(running.Lease.Lifecycle.Snapshot.Modules,
            module => module.ModuleId == "protocol").Status);
        await LifecycleTestHarness.Until(() => validated.Composition.EnabledModuleIds.All(id => registry.Probes[id].Workers == 1));
        observation.Write("optional-unavailable", validated.Composition, running);
        await running.DisposeAsync();
        Inactive(disabled);
        Assert.True(running.Lease.StopResult!.Complete);
        if (!observation.Write("optional-unavailable-stopped", validated.Composition, running))
        { Observe($"CP-12/{target}", registry, running.Lease); }

        var repair = new Registry();
        repair.Protocol();
        repair.Replace("metadata", declaration => declaration with { Dependencies = [Dependency("identity", true)] });
        repair.Probes["identity"] = Add<Identity>(repair.Builder, Declaration("identity", ModuleCategory.Identity) with
        { Capabilities = [new() { Id = "integration", Version = "0.1.0", Description = "Enabled target supplies this." }] });
        var repairObservation = new MatrixObservation(output, identity, repair);
        var repaired = repair.Validate(Selection("identity") with
        { RequiredCapabilities = [new("identity", "integration", "[0.1.0]", false)] }).Composition!;
        Assert.Single(repaired.ActiveEdges);
        Assert.Single(repaired.SatisfiedCapabilities);
        await using var available = await repair.BuildAsync(repaired);
        await available.StartAsync();
        Assert.True(available.Lease.Lifecycle.Snapshot.Ready);
        Inactive(repair.Probes["protocol"]);
        await LifecycleTestHarness.Until(() => repaired.EnabledModuleIds.All(id => repair.Probes[id].Workers == 1));
        repairObservation.Write("optional-enabled", repaired, available);
        await available.DisposeAsync();
        Assert.True(available.Lease.StopResult!.Complete);
        if (!repairObservation.Write("optional-enabled-stopped", repaired, available))
        { Observe($"CP-12/{target}/explicit-repair", repair, available.Lease); }
    }

    [Theory]
    [InlineData("CP-14", "initialize")]
    public async Task Required_initialization_failure_has_no_readiness_or_fallback_and_cleans_owner(string id, string phase)
    {
        var registry = new Registry();
        await using var logs = new LifecycleTestHarness();
        registry.Web.Logging.AddProvider(logs);
        registry.Probes["artifact-other"] = Add<ArtifactOther>(registry.Builder, Declaration("artifact-other", ModuleCategory.Artifact));
        var callback = new OwnershipFixtures.ControlledCallback(cooperative: true, failAfterRelease: true);
        callback.Release();
        registry.Probes["artifact"].Initialize = callback.RunAsync;
        var observation = new OwnershipObservation(output,
            $"{typeof(ConformanceMatrixTests).FullName}.{nameof(Required_initialization_failure_has_no_readiness_or_fallback_and_cleans_owner)}(id: \"{id}\", phase: \"{phase}\")",
            registry, callback);
        await using var running = await registry.BuildAsync(registry.Validate().Composition!);
        await running.App.MapHoardModulesAsync(running.Lease);
        var result = await running.Lease.Lifecycle.StartAsync();
        await callback.Entered.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.False(result.Ready);
        Assert.False(running.Lease.Lifecycle.Snapshot.StartupAdmission);
        Assert.Contains(result.Diagnostics, item => item.RuleCode == "PhaseFailure" && item.ModuleId == "artifact");
        Safe(result.Diagnostics);
        SafeFailure(logs, result, running.Lease.Lifecycle.Snapshot);
        Assert.Equal(0, registry.Probes["artifact"].Workers);
        Assert.Equal(0, registry.Probes["artifact"].Assessments);
        Inactive(registry.Probes["artifact-other"]);
        observation.Write("initialization-denied", running.Lease);
        await running.DisposeAsync();
        Assert.True(running.Lease.StopResult!.Complete);
        Assert.Equal(1, registry.Probes["artifact"].Stops);
        Assert.Equal(1, registry.Probes["artifact"].Disposals);
        SafeFailure(logs, running.Lease.StopResult, running.Lease.Lifecycle.Snapshot);
        if (!observation.Write("ownership-stopped", running.Lease))
        { Observe($"{id}/{phase}", registry, running.Lease); }
    }

    [Theory]
    [InlineData("initialize")]
    [InlineData("readiness")]
    public async Task CP15_cancelled_caller_does_not_admit_or_release_pending_shared_work(string phase)
    {
        var registry = new Registry();
        var callback = new OwnershipFixtures.ControlledCallback(cooperative: true);
        var observation = new OwnershipObservation(output,
            $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP15_cancelled_caller_does_not_admit_or_release_pending_shared_work)}(phase: \"{phase}\")",
            registry, callback);
#if CONFORMANCE_PROVIDER_PACKAGES
        Assert.Equal("Hoard.Fixtures.Conformance.Host", callback.GetType().Assembly.GetName().Name);
#endif
        if (phase == "initialize")
        {
            registry.Probes["artifact"].Initialize = callback.RunAsync;
        }
        else
        {
            registry.Probes["artifact"].Assess = async token =>
            {
                await callback.RunAsync(token);
                return new(true, []);
            };
        }
        await using var running = await registry.BuildAsync(registry.Validate().Composition!);
        await running.App.MapHoardModulesAsync(running.Lease);
        using var cancelled = new CancellationTokenSource();
        var start = running.Lease.Lifecycle.StartAsync(cancelled.Token);
        try
        {
            await callback.Entered.WaitAsync(TimeSpan.FromSeconds(5));
            cancelled.Cancel();
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() => start.WaitAsync(TimeSpan.FromSeconds(5)));
            Assert.False(callback.Settled.IsCompleted);
            Assert.False(running.Lease.Lifecycle.Snapshot.Ready);
            Assert.False(running.Lease.Lifecycle.Snapshot.StartupAdmission);
            Assert.Equal(0, registry.Probes["artifact"].Stops);
            Assert.Equal(0, registry.Probes["artifact"].Disposals);
            Assert.Equal(1, registry.Probes["artifact"].Initializations);
            Assert.Equal(phase == "initialize" ? 0 : 1, registry.Probes["artifact"].Assessments);
            Assert.Equal(0, registry.Probes["artifact"].Workers);
            if (!observation.Write("caller-cancelled", running.Lease))
            {
                output.WriteLine($"CP-15/{phase}/cancelled-wait: caller-cancelled=1; callback-settled=0; ready=0; admission=0; stops=0; disposals=0");
            }
            var stop = await running.Lease.Lifecycle.StopAsync().WaitAsync(TimeSpan.FromSeconds(5));
            await callback.Settled.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Empty(stop.UnsafeActivities);
            Assert.False(running.Lease.Lifecycle.Snapshot.Ready);
            Assert.False(running.Lease.Lifecycle.Snapshot.StartupAdmission);
            await running.DisposeAsync();
            Assert.True(running.Lease.StopResult!.Complete);
            if (!observation.Write("ownership-stopped", running.Lease))
            { Observe($"CP-15/{phase}", registry, running.Lease); }
        }
        finally { callback.Release(); }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CP16_noncooperative_initializer_returns_finitely_but_retains_owner_until_real_settlement(bool lateFault)
    {
        var registry = new Registry();
        await using var logs = new LifecycleTestHarness();
        registry.Web.Logging.AddProvider(logs);
        var clock = new LifecycleTestTimeProvider();
        var callback = new OwnershipFixtures.ControlledCallback(cooperative: false, failAfterRelease: lateFault);
        var observation = new OwnershipObservation(output,
            $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP16_noncooperative_initializer_returns_finitely_but_retains_owner_until_real_settlement)}(lateFault: {lateFault})",
            registry, callback);
        registry.Probes["artifact"].Initialize = callback.RunAsync;
        var composition = registry.Validate(options: new()
        {
            ActivationCallbackTimeout = TimeSpan.FromSeconds(1),
            DrainTimeout = TimeSpan.FromSeconds(1)
        }, clock: clock).Composition!;
        var running = await registry.BuildAsync(composition);
        await running.App.MapHoardModulesAsync(running.Lease);
        var start = running.Lease.Lifecycle.StartAsync();
        try
        {
            await callback.Entered.WaitAsync(TimeSpan.FromSeconds(5));
            await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            await LifecycleTestHarness.Until(() => running.Lease.Lifecycle.Snapshot.Phase == HoardLifecyclePhase.Draining
                && clock.NextDelay == TimeSpan.FromSeconds(1));
            clock.Advance(TimeSpan.FromSeconds(1));
            Assert.False((await start.WaitAsync(TimeSpan.FromSeconds(5))).Ready);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => running.DisposeAsync().AsTask());
            var retained = running.Lease.StopResult!;
            Assert.False(retained.Complete);
            Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, retained.RootDisposal);
            Assert.Equal(new HoardUnsafeActivity("artifact", HoardActivityKind.Phase), Assert.Single(retained.UnsafeActivities));
            Assert.Equal(0, registry.Probes["artifact"].Stops);
            Assert.Equal(0, registry.Probes["artifact"].Disposals);
            Assert.Equal(1, registry.Probes["artifact"].Initializations);
            Assert.Equal(0, registry.Probes["artifact"].Assessments);
            Assert.Equal(0, registry.Probes["artifact"].Workers);
            Assert.False(registry.Probes["artifact"].Settled.Task.IsCompleted);
            Assert.False(callback.Settled.IsCompleted);
            Assert.False(running.Lease.Lifecycle.Snapshot.StartupAdmission);
            if (!observation.Write("ownership-retained", running.Lease))
            {
                output.WriteLine($"CP-16/retained: caller-returned=1; callback-settled=0; unsafe={retained.UnsafeActivities.Length}; " +
                    $"root-disposal={(int)retained.RootDisposal}; stops=0; disposals=0; admission=0");
            }
            callback.Release();
            await registry.Probes["artifact"].Settled.Task.WaitAsync(TimeSpan.FromSeconds(5));
            var work = registry.Probes["artifact"].InitializationWork!;
            if (lateFault)
            {
                await Assert.ThrowsAsync<InvalidOperationException>(() => work.WaitAsync(TimeSpan.FromSeconds(5)));
                await LifecycleTestHarness.Until(() => running.Lease.Lifecycle.Snapshot.Diagnostics.Any(item => item.RuleCode == "LateCallbackFailure"));
                Assert.Single(running.Lease.Lifecycle.Snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
                Assert.DoesNotContain(retained.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
            }
            else { await work.WaitAsync(TimeSpan.FromSeconds(5)); }
            Assert.True(callback.Settled.IsCompletedSuccessfully);
            Assert.False(running.Lease.Lifecycle.Snapshot.Ready);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => running.DisposeAsync().AsTask());
            Assert.Same(retained, running.Lease.StopResult);
            Assert.False((await running.Lease.Lifecycle.StartAsync().WaitAsync(TimeSpan.FromSeconds(5))).Ready);
            Assert.Equal(1, registry.Probes["artifact"].Constructors);
            Assert.Equal(1, registry.Probes["artifact"].Initializations);
            Assert.Equal(0, registry.Probes["artifact"].Stops);
            Assert.Equal(0, registry.Probes["artifact"].Disposals);
            Safe(running.Lease.Lifecycle.Snapshot.Diagnostics);
            SafeFailure(logs, retained, running.Lease.Lifecycle.Snapshot);
            if (!observation.Write("ownership-settled", running.Lease))
            {
                output.WriteLine("CP-16/settled: callback-settled=1; underlying-task-completed=1; frozen-incomplete=1; disposals=0");
                Observe("CP-16/settled-not-reclassified", registry, running.Lease);
            }
        }
        finally
        {
            callback.Release();
            await start.WaitAsync(TimeSpan.FromSeconds(5));
            await registry.Probes["artifact"].Settled.Task.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Theory]
    [InlineData("fault")]
    [InlineData("noncooperative")]
    [InlineData("noncooperative-fault")]
    public async Task CP17_shutdown_fault_or_retention_never_claims_complete_cleanup(string variant)
    {
        var registry = new Registry();
        await using var logs = new LifecycleTestHarness();
        registry.Web.Logging.AddProvider(logs);
        var clock = new LifecycleTestTimeProvider();
        var callback = new OwnershipFixtures.ControlledCallback(
            cooperative: false, failAfterRelease: variant != "noncooperative");
        var observation = new OwnershipObservation(output,
            $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP17_shutdown_fault_or_retention_never_claims_complete_cleanup)}(variant: \"{variant}\")",
            registry, callback);
        if (variant == "fault") { callback.Release(); }
        registry.Probes["artifact"].Stop = callback.RunAsync;
        var composition = registry.Validate(options: new() { ModuleCleanupTimeout = TimeSpan.FromSeconds(1) }, clock: clock).Composition!;
        var running = await registry.BuildAsync(composition);
        await running.StartAsync();
        var stopping = running.Lease.Lifecycle.StopAsync();
        try
        {
            await callback.Entered.WaitAsync(TimeSpan.FromSeconds(5));
            if (variant != "fault")
            {
                await LifecycleTestHarness.Until(() => clock.NextDelay == TimeSpan.FromSeconds(1));
                clock.Advance(TimeSpan.FromSeconds(1));
            }
            var stopped = await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(variant == "fault" ? HoardCleanupOutcome.Failed : HoardCleanupOutcome.TimedOut,
                Assert.Single(stopped.Modules, module => module.ModuleId == "artifact").Outcome);
            Assert.False(stopped.Complete);
            Assert.False(running.Lease.Lifecycle.Snapshot.Ready);
            Assert.False(running.Lease.Lifecycle.Snapshot.StartupAdmission);
            Assert.Equal(1, registry.Probes["artifact"].Stops);
            await Assert.ThrowsAsync<HoardLifecycleException>(() => running.DisposeAsync().AsTask());
            if (variant != "fault")
            {
                Assert.False(callback.Settled.IsCompleted);
                Assert.Equal(0, registry.Probes["artifact"].Disposals);
                Assert.Equal(HoardRootDisposalOutcome.NotAttemptedUnsafe, running.Lease.StopResult!.RootDisposal);
                Assert.Equal("artifact", Assert.Single(running.Lease.StopResult.UnsafeActivities).ModuleId);
                if (!observation.Write("ownership-retained", running.Lease))
                {
                    output.WriteLine($"CP-17/noncooperative/retained: caller-returned=1; callback-settled=0; " +
                        $"unsafe={running.Lease.StopResult.UnsafeActivities.Length}; disposals=0; complete=0");
                }
            }
            var frozen = running.Lease.StopResult;
            callback.Release();
            await callback.Settled.WaitAsync(TimeSpan.FromSeconds(5));
            if (variant == "noncooperative-fault")
            {
                await Assert.ThrowsAsync<InvalidOperationException>(() =>
                    registry.Probes["artifact"].ShutdownWork!.WaitAsync(TimeSpan.FromSeconds(5)));
                await LifecycleTestHarness.Until(() => running.Lease.Lifecycle.Snapshot.Diagnostics.Any(item => item.RuleCode == "LateCallbackFailure"));
                Assert.Single(running.Lease.Lifecycle.Snapshot.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
                Assert.DoesNotContain(frozen!.Diagnostics, item => item.RuleCode == "LateCallbackFailure");
            }
            else if (variant == "noncooperative")
            { await registry.Probes["artifact"].ShutdownWork!.WaitAsync(TimeSpan.FromSeconds(5)); }
            await Assert.ThrowsAsync<HoardLifecycleException>(() => running.DisposeAsync().AsTask());
            Assert.Same(frozen, running.Lease.StopResult);
            Assert.False((await running.Lease.Lifecycle.StartAsync().WaitAsync(TimeSpan.FromSeconds(5))).Ready);
            Assert.Equal(1, registry.Probes["artifact"].Constructors);
            Assert.Equal(1, registry.Probes["artifact"].Initializations);
            Assert.Equal(1, registry.Probes["artifact"].Stops);
            if (variant != "fault") { Assert.Equal(0, registry.Probes["artifact"].Disposals); }
            Safe(running.Lease.Lifecycle.Snapshot.Diagnostics);
            SafeFailure(logs, frozen, running.Lease.Lifecycle.Snapshot);
            if (!observation.Write("ownership-settled", running.Lease))
            {
                output.WriteLine($"CP-17/{variant}/settled: callback-settled=1; frozen-incomplete=1");
                Observe($"CP-17/{variant}", registry, running.Lease);
            }
        }
        finally
        {
            callback.Release();
            await stopping.WaitAsync(TimeSpan.FromSeconds(5));
            await callback.Settled.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Fact]
    public async Task CP20_active_selection_is_immutable_and_only_fresh_settled_restart_changes_owner()
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP20_active_selection_is_immutable_and_only_fresh_settled_restart_changes_owner)}";
        Guid previous;
        var first = new Registry();
        first.Protocol();
        first.Probes["metadata-other"] = Add<MetadataOther>(first.Builder, Declaration("metadata-other", ModuleCategory.Metadata));
        first.Probes["artifact-other"] = Add<ArtifactOther>(first.Builder, Declaration("artifact-other", ModuleCategory.Artifact));
        var firstObservation = new RestartObservation(output, identity, first,
            [first.Probes["protocol"], first.Probes["metadata-other"], first.Probes["artifact-other"]]);
        var selection = Selection();
        var composition = first.Validate(selection).Composition!;
        await using (var running = await first.BuildAsync(composition))
        {
            await running.StartAsync();
            previous = running.Lease.Lifecycle.Snapshot.CompositionIdentity;
            selection = selection with
            {
                EnabledModuleIds = ["metadata-other", "artifact-other", "protocol"],
                MetadataModuleId = "metadata-other",
                ArtifactModuleId = "artifact-other"
            };
            var changed = first.Validate(selection).Composition!;
            Assert.Contains("protocol", changed.EnabledModuleIds);
            Assert.DoesNotContain("protocol", composition.EnabledModuleIds);
            using var client = running.App.GetTestClient();
            Assert.Equal("conformance", await client.GetStringAsync("/metadata"));
            using var inactive = await client.GetAsync("/protocol");
            Assert.Equal(HttpStatusCode.NotFound, inactive.StatusCode);
            Inactive(first.Probes["protocol"]);
            Inactive(first.Probes["metadata-other"]);
            Inactive(first.Probes["artifact-other"]);
            Assert.Equal(previous, running.Lease.Lifecycle.Snapshot.CompositionIdentity);
            await LifecycleTestHarness.Until(() => first.Probes["metadata"].Workers == 1 && first.Probes["artifact"].Workers == 1);
            firstObservation.Write("selection-fixed", running.Lease,
                running.Lease.Lifecycle.Snapshot.Modules.Where(module => module.Enabled)
                    .Select(module => module.ModuleId).Order().SequenceEqual(composition.EnabledModuleIds.Order()), false);
            await running.DisposeAsync();
            Assert.True(running.Lease.StopResult!.Complete);
            Assert.False((await running.Lease.Lifecycle.StartAsync()).Ready);
            if (!firstObservation.Write("selection-stopped", running.Lease,
                previous == running.Lease.Lifecycle.Snapshot.CompositionIdentity, false))
            { Observe("CP-20/active-selection", first, running.Lease); }
        }
        var second = new Registry();
        second.Protocol();
        second.Probes["metadata-other"] = Add<MetadataOther>(second.Builder, Declaration("metadata-other", ModuleCategory.Metadata));
        second.Probes["artifact-other"] = Add<ArtifactOther>(second.Builder, Declaration("artifact-other", ModuleCategory.Artifact));
        var secondObservation = new RestartObservation(output, identity, second,
            [second.Probes["metadata"], second.Probes["artifact"]]);
        await using var restarted = await second.BuildAsync(second.Validate(selection).Composition!);
        await restarted.StartAsync();
        Assert.NotEqual(previous, restarted.Lease.Lifecycle.Snapshot.CompositionIdentity);
        using var restartedClient = restarted.App.GetTestClient();
        Assert.Equal("conformance", await restartedClient.GetStringAsync("/protocol"));
        Assert.Equal("conformance", await restartedClient.GetStringAsync("/metadata-other"));
        Assert.Equal("conformance", await restartedClient.GetStringAsync("/artifact-other"));
        Inactive(second.Probes["metadata"]);
        Inactive(second.Probes["artifact"]);
        await LifecycleTestHarness.Until(() => second.Probes["protocol"].Workers == 1
            && second.Probes["metadata-other"].Workers == 1 && second.Probes["artifact-other"].Workers == 1);
        secondObservation.Write("selection-restarted", restarted.Lease,
            restarted.Lease.Lifecycle.Snapshot.Modules.Where(module => module.Enabled)
                .Select(module => module.ModuleId).Order().SequenceEqual(selection.EnabledModuleIds.Order()),
            previous != restarted.Lease.Lifecycle.Snapshot.CompositionIdentity);
        await restarted.DisposeAsync();
        Assert.True(restarted.Lease.StopResult!.Complete);
        Assert.Equal(1, second.Probes["protocol"].Disposals);
        if (!secondObservation.Write("restart-stopped", restarted.Lease,
            restarted.Lease.Lifecycle.Snapshot.Modules.Where(module => module.Enabled)
                .Select(module => module.ModuleId).Order().SequenceEqual(selection.EnabledModuleIds.Order()),
            previous != restarted.Lease.Lifecycle.Snapshot.CompositionIdentity))
        { Observe("CP-20/explicit-restart", second, restarted.Lease); }
    }

    [Fact]
    public async Task CP20_active_configuration_is_fixed_until_a_fresh_explicit_restart()
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP20_active_configuration_is_fixed_until_a_fresh_explicit_restart)}";
        Guid? previousIdentity = null;
        static string Document(string value) => JsonSerializer.Serialize(new
        {
            configurationVersion = 1,
            enabledModules = new[] { "metadata", "artifact" },
            metadataModule = "metadata",
            artifactModule = "artifact",
            identityModules = Array.Empty<string>(),
            requiredCapabilities = Array.Empty<object>(),
            modules = new Dictionary<string, object>
            {
                ["metadata"] = new { optionsVersion = 1, options = new { label = value } },
                ["artifact"] = new { optionsVersion = 1, options = new { } }
            }
        });
        for (var iteration = 0; iteration < 2; iteration++)
        {
            var registry = new Registry();
            registry.Replace("metadata", declaration => declaration with
            { Configuration = [new() { Key = "label", Description = "Restart-only setting.", Required = true, SecretReference = false }] });
            registry.Builder.AddModuleConfiguration<Metadata>(new(1, [new("label", HoardOptionType.String, true)]));
            await using var evaluation = await registry.Builder.EvaluateConfigurationAsync(
                new(Document(iteration == 0 ? "first" : "second")), Versions, new());
            Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
            await using var lease = await registry.Builder.ComposeHoardModulesAsync(evaluation.Configuration!);
            var app = await registry.Web.BuildHoardApplicationAsync(lease);
            await app.MapHoardModulesAsync(lease);
            await app.StartAsync();
            var active = registry.Probes["metadata"].Options!;
            Assert.Equal(iteration == 0 ? "first" : "second", active.GetString("label"));
            var callback = new OwnershipFixtures.ControlledCallback(cooperative: false);
            var observation = new RestartObservation(output, identity, registry, [], callback);
            var identityChanged = previousIdentity is { } previous && previous != lease.Lifecycle.Snapshot.CompositionIdentity;
            bool ConfigurationFixed() => ReferenceEquals(active, registry.Probes["metadata"].Options)
                && active.GetString("label") == (iteration == 0 ? "first" : "second");
            registry.Probes["metadata"].Request = callback.RunAsync;
#if CONFORMANCE_PROVIDER_PACKAGES
            Assert.Equal("Hoard.Fixtures.Conformance.Host",
                registry.Probes["metadata"].Request!.Method.DeclaringType!.Assembly.GetName().Name);
#endif
            using var client = app.GetTestClient();
            var request = client.GetStringAsync("/metadata");
            Task? stopping = null;
            try
            {
                await callback.Entered.WaitAsync(TimeSpan.FromSeconds(5));
                await LifecycleTestHarness.Until(() => registry.Probes.Values.All(probe => probe.Workers == 1));
                await using var changed = await registry.Builder.EvaluateConfigurationAsync(new(Document("second")), Versions, new());
                Assert.Equal(HoardConfigurationOutcome.Validated, changed.Outcome);
                Assert.False(request.IsCompleted);
                Assert.Same(active, registry.Probes["metadata"].Options);
                Assert.Equal(iteration == 0 ? "first" : "second", active.GetString("label"));
                Assert.True(lease.Lifecycle.Snapshot.Ready);
                observation.Write(iteration == 0 ? "configuration-active" : "configuration-restarted",
                    lease, ConfigurationFixed(), identityChanged, request);
                stopping = app.StopHoardApplicationAsync(lease);
                await LifecycleTestHarness.Until(() => lease.Lifecycle.Snapshot.Phase == HoardLifecyclePhase.Draining);
                Assert.False(stopping.IsCompleted);
                Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
                Assert.False(lease.Lifecycle.Snapshot.Ready);
                Assert.Equal(0, registry.Probes["metadata"].Stops);
                Assert.Equal(0, registry.Probes["metadata"].Disposals);
                using var denied = await client.GetAsync("/metadata").WaitAsync(TimeSpan.FromSeconds(5));
                Assert.Equal(HttpStatusCode.ServiceUnavailable, denied.StatusCode);
                Assert.Equal(1, registry.Probes["metadata"].Requests);
                observation.Write(iteration == 0 ? "configuration-draining" : "restart-draining",
                    lease, ConfigurationFixed(), identityChanged, request);
            }
            finally { callback.Release(); }
            Assert.Equal("conformance", await request.WaitAsync(TimeSpan.FromSeconds(5)));
            await stopping!.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal(1, registry.Probes["metadata"].Constructors);
            await lease.DisposeAsync();
            Assert.True(lease.StopResult!.Complete);
            if (!observation.Write(iteration == 0 ? "configuration-stopped" : "restart-stopped",
                lease, ConfigurationFixed(), identityChanged, request))
            { Observe($"CP-20/configuration/restart-{iteration}", registry, lease); }
            previousIdentity = lease.Lifecycle.Snapshot.CompositionIdentity;
        }
    }

#if CONFORMANCE_PROVIDER_PACKAGES
    [Theory]
    [InlineData("CP-01", "sqlite", "local", "Hoard.Fixtures.Metadata.Sqlite", "Hoard.Fixtures.Artifacts.Local")]
    [InlineData("CP-02", "memory", "object", "Hoard.Fixtures.Metadata.Memory", "Hoard.Fixtures.Artifacts.ObjectSemantics")]
    public async Task Packaged_baseline_and_replacement_use_the_identical_consumer(string id, string metadata,
        string artifact, string metadataAssembly, string artifactAssembly)
    {
        Assert.Equal("Hoard.Fixtures.Conformance.Host", typeof(PackagedComposition).Assembly.GetName().Name);
        await using var fixture = new PackagedComposition();
        await using var evaluation = await fixture.Builder.EvaluateConfigurationAsync(
            new(fixture.Configuration(metadata, artifact)), Versions, new());
        Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
        await using var lease = await fixture.Builder.ComposeHoardModulesAsync(evaluation.Configuration!);
        var app = await fixture.Web.BuildHoardApplicationAsync(lease);
        await app.MapHoardModulesAsync(lease);
        var metadataModules = app.Services.GetServices<MetadataFixtureModule>().ToArray();
        var artifactModules = app.Services.GetServices<ArtifactFixtureModule>().ToArray();
        var metadataModule = Assert.Single(metadataModules);
        var artifactModule = Assert.Single(artifactModules);
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(Packaged_baseline_and_replacement_use_the_identical_consumer)}" +
            $"(id: \"{id}\", metadata: \"{metadata}\", artifact: \"{artifact}\", metadataAssembly: \"{metadataAssembly}\", artifactAssembly: \"{artifactAssembly}\")";
        var owner = ConformanceOriginalObservationOutput.WriteIfRequested(output, identity, "none",
            "original-owner", null, null, ("owner", fixture));
        var metadataReady = (await metadataModule.CheckReadinessAsync(default)).Ready;
        var artifactReady = (await artifactModule.CheckReadinessAsync(default)).Ready;
        Assert.False(metadataReady);
        Assert.False(artifactReady);
        Assert.False(lease.Lifecycle.Snapshot.StartupAdmission);
        Assert.All(fixture.Probes.Values, probe =>
        {
            Assert.Equal(1, probe.Constructors);
            Assert.Equal(1, probe.Maps);
            Assert.Equal(0, probe.Initializations);
            Assert.Equal(0, probe.Assessments);
            Assert.Equal(0, probe.Workers);
            Assert.Equal(0, probe.Connections);
        });
        Assert.False(File.Exists(fixture.DatabasePath));
        Assert.False(Directory.Exists(fixture.ArtifactRoot));
        Assert.False(Directory.Exists(fixture.DisabledRoot));
        Snapshot("before-initialization", metadataReady, artifactReady);
        await app.StartAsync();
        Assert.True(lease.Lifecycle.Snapshot.Ready);
        metadataReady = (await metadataModule.CheckReadinessAsync(default)).Ready;
        artifactReady = (await artifactModule.CheckReadinessAsync(default)).Ready;
        Assert.True(metadataReady);
        Assert.True(artifactReady);
        Assert.Equal(metadataAssembly, metadataModule.Session.Store.GetType().Assembly.GetName().Name);
        Assert.Equal(artifactAssembly, artifactModule.Session.Store.GetType().Assembly.GetName().Name);
        var inspected = Assert.IsType<MetadataResult<MetadataSchemaInspection>.Success>(
            await metadataModule.Session.Schema.InspectAsync(new(), default));
        Assert.Equal(MetadataSchemaState.Compatible, inspected.Value.State);
        Assert.True(artifactModule.Session.Capabilities.MeetsBaseline);
        using var client = app.GetTestClient();
        Assert.Equal("conformance", await client.GetStringAsync("/protocol"));
        Assert.Equal("conformance", await client.GetStringAsync("/identity"));
        await LifecycleTestHarness.Until(() => fixture.Probes.Values.All(probe => probe.Workers == 1));
        Assert.All(fixture.Probes.Values, probe =>
        {
            Assert.Equal(1, probe.Initializations);
            Assert.Equal(1, probe.Assessments);
            Assert.Equal(1, probe.Connections);
            Assert.Equal(1, probe.Requests);
        });
        Assert.False(Directory.Exists(fixture.DisabledRoot));
        Snapshot("ready", metadataReady, artifactReady);
        await lease.DisposeAsync();
        Assert.True(lease.StopResult!.Complete);
        metadataReady = (await metadataModule.CheckReadinessAsync(default)).Ready;
        Assert.False(metadataReady);
        Assert.False(artifactModule.Session.Ready);
        Assert.All(fixture.Probes.Values, probe =>
        {
            Assert.Equal(1, probe.Stops);
            Assert.Equal(1, probe.Disposals);
        });
        Snapshot("stopped", metadataReady, artifactModule.Session.Ready);
        if (owner is null)
        {
            output.WriteLine($"{id}/{metadata}/{artifact}: metadata-singletons=1; artifact-singletons=1; schema-compatible=1; " +
                "initial-admission=0; ready-after-initialize=1; protocol-requests=1; identity-requests=1; disabled-roots=0; stop-complete=1");
        }

        void Snapshot(string stage, bool metadataIsReady, bool artifactIsReady)
        {
            if (owner is null) { return; }
            ConformanceCompositionObservationOutput.Write(output, owner, stage, new Dictionary<string, int>(StringComparer.Ordinal)
            {
                ["metadataSingletons"] = metadataModules.Length,
                ["artifactSingletons"] = artifactModules.Length,
                ["metadataReady"] = metadataIsReady ? 1 : 0,
                ["artifactReady"] = artifactIsReady ? 1 : 0,
                ["ready"] = lease.Lifecycle.Snapshot.Ready ? 1 : 0,
                ["admission"] = lease.Lifecycle.Snapshot.StartupAdmission ? 1 : 0,
                ["disabledRoots"] = Directory.Exists(fixture.DisabledRoot) ? 1 : 0,
                ["protocolRequests"] = fixture.Probes["protocol"].Requests,
                ["identityRequests"] = fixture.Probes["identity"].Requests,
                ["stopComplete"] = lease.StopResult?.Complete == true ? 1 : 0,
                ["unsafeActivities"] = lease.StopResult?.UnsafeActivities.Length ?? 0
            });
        }
    }

    private sealed class AdmissionObservation(ITestOutputHelper output, string identity, PackagedComposition fixture)
    {
        private readonly ConformanceOriginalObservation? owner =
            ConformanceOriginalObservationOutput.WriteIfRequested(
                output, identity, "none", "original-owner", null, null, ("owner", fixture));

        public bool Write(string stage, HoardServiceComposition lease, HoardStartResult start)
        {
            if (owner is null) { return false; }
            ConformanceCompositionObservationOutput.Write(output, owner, stage,
                new Dictionary<string, int>(StringComparer.Ordinal)
                {
                    ["ready"] = lease.Lifecycle.Snapshot.Ready ? 1 : 0,
                    ["admission"] = lease.Lifecycle.Snapshot.StartupAdmission ? 1 : 0,
                    ["phaseFailures"] = start.Diagnostics.Count(item => item.RuleCode == "PhaseFailure"),
                    ["fallbackRoots"] = Directory.Exists(fixture.DisabledRoot) ? 1 : 0,
                    ["workers"] = fixture.Probes.Values.Sum(probe => probe.Workers),
                    ["stopComplete"] = lease.StopResult?.Complete == true ? 1 : 0,
                    ["rootDisposal"] = (int?)(lease.StopResult?.RootDisposal) ?? 6,
                    ["unsafeActivities"] = lease.StopResult?.UnsafeActivities.Length ?? 0
                });
            return true;
        }
    }

    [Theory]
    [InlineData("sqlite")]
    [InlineData("memory")]
    public async Task CP14_schema_admission_denies_empty_store_without_explicit_create_and_repair_succeeds(string provider)
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP14_schema_admission_denies_empty_store_without_explicit_create_and_repair_succeeds)}(provider: \"{provider}\")";
        foreach (var createEmpty in new[] { false, true })
        {
            await using var fixture = new PackagedComposition();
            var observation = new AdmissionObservation(output, identity, fixture);
            await using var evaluation = await fixture.Builder.EvaluateConfigurationAsync(
                new(fixture.Configuration(provider, "object", createEmpty)), Versions, new());
            Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
            await using var lease = await fixture.Builder.ComposeHoardModulesAsync(evaluation.Configuration!);
            var app = await fixture.Web.BuildHoardApplicationAsync(lease);
            await app.MapHoardModulesAsync(lease);
            var result = await lease.Lifecycle.StartAsync();
            Assert.Equal(createEmpty, result.Ready);
            Assert.Equal(createEmpty, lease.Lifecycle.Snapshot.StartupAdmission);
            if (!createEmpty)
            {
                Assert.Contains(result.Diagnostics, item => item.ModuleId == "fixture.metadata" && item.RuleCode == "PhaseFailure");
                Safe(result.Diagnostics);
                Assert.All(fixture.Probes.Values, probe => Assert.Equal(0, probe.Workers));
            }
            Assert.False(Directory.Exists(fixture.DisabledRoot));
            if (createEmpty)
            { await LifecycleTestHarness.Until(() => fixture.Probes.Values.All(probe => probe.Workers == 1)); }
            observation.Write(createEmpty ? "repair-admitted" : "admission-denied", lease, result);
            await lease.DisposeAsync();
            Assert.True(lease.StopResult!.Complete);
            if (!observation.Write(createEmpty ? "repair-stopped" : "denial-stopped", lease, result))
            { output.WriteLine($"CP-14/schema/{provider}/create-{createEmpty}: admission={(result.Ready ? 1 : 0)}; fallback-roots=0; stop-complete=1"); }
        }
    }

    [Fact]
    public async Task CP18_real_local_recovery_rejects_corrupt_manifest_without_fallback_and_exact_repair_recovers()
    {
        var testIdentity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP18_real_local_recovery_rejects_corrupt_manifest_without_fallback_and_exact_repair_recovers)}";
        await using var owner = new PackagedComposition();
        ArtifactStoreIdentity identity;
        await using (var initial = await ArtifactFixtureSession.CreateForQualificationAsync("local", owner.ArtifactRoot))
        { identity = initial.Identity; }
        var manifest = Path.Combine(owner.ArtifactRoot, "local-manifest.json");
        var original = await File.ReadAllBytesAsync(manifest);
        await File.WriteAllTextAsync(manifest, "credential=conformance-secret");
        foreach (var repaired in new[] { false, true })
        {
            if (repaired) { await File.WriteAllBytesAsync(manifest, original); }
            await using var fixture = new PackagedComposition(owner.Root);
            var observation = new AdmissionObservation(output, testIdentity, fixture);
            fixture.Web.Services.AddSingleton(new ArtifactFixtureAdmissionProfile
            { Mode = ArtifactInitializationMode.ReopenCompatible, Store = identity });
            await using var evaluation = await fixture.Builder.EvaluateConfigurationAsync(
                new(fixture.Configuration("memory", "local")), Versions, new());
            Assert.Equal(HoardConfigurationOutcome.Validated, evaluation.Outcome);
            await using var lease = await fixture.Builder.ComposeHoardModulesAsync(evaluation.Configuration!);
            var app = await fixture.Web.BuildHoardApplicationAsync(lease);
            await app.MapHoardModulesAsync(lease);
            var result = await lease.Lifecycle.StartAsync();
            Assert.Equal(repaired, result.Ready);
            Assert.Equal(repaired, lease.Lifecycle.Snapshot.StartupAdmission);
            if (!repaired)
            {
                Assert.Contains(result.Diagnostics, item => item.ModuleId == "fixture.artifact" && item.RuleCode == "PhaseFailure");
                Safe(result.Diagnostics);
                Assert.All(fixture.Probes.Values, probe => Assert.Equal(0, probe.Workers));
            }
            Assert.False(Directory.Exists(fixture.DisabledRoot));
            if (repaired)
            { await LifecycleTestHarness.Until(() => fixture.Probes.Values.All(probe => probe.Workers == 1)); }
            observation.Write(repaired ? "repair-admitted" : "admission-denied", lease, result);
            await lease.DisposeAsync();
            Assert.True(lease.StopResult!.Complete);
            if (!observation.Write(repaired ? "repair-stopped" : "denial-stopped", lease, result))
            { output.WriteLine($"CP-18/local/repaired-{repaired}: ready={(result.Ready ? 1 : 0)}; alternate-roots=0; stop-complete=1"); }
        }
    }

    [Theory]
    [InlineData("authority-identity")]
    [InlineData("mandatory-guarantee")]
    public async Task CP19_actual_store_admission_rejects_before_io_and_paired_repair_admits(string variant)
    {
        var identity = $"{typeof(ConformanceMatrixTests).FullName}.{nameof(CP19_actual_store_admission_rejects_before_io_and_paired_repair_admits)}(variant: \"{variant}\")";
        foreach (var repaired in new[] { false, true })
        {
            await using var directory = new PackagedComposition();
            var registry = new Registry();
            registry.Probes["artifact-other"] = Add<ArtifactOther>(registry.Builder, Declaration("artifact-other", ModuleCategory.Artifact));
            var admission = new OwnershipFixtures.ControlledAdmission(directory.ArtifactRoot, variant, repaired);
            var observation = new StoreAdmissionObservation(output, identity, registry, admission);
            var controls = admission.Controls;
            var store = admission.Store;
            registry.Probes["artifact"].Initialize = admission.InitializeAsync;
            registry.Probes["artifact"].Stop = admission.StopAsync;
            Assert.Equal("Hoard.Fixtures.Conformance.Host",
                registry.Probes["artifact"].Initialize!.Method.DeclaringType!.Assembly.GetName().Name);
            Assert.Equal("Hoard.Fixtures.Conformance.Host",
                registry.Probes["artifact"].Stop!.Method.DeclaringType!.Assembly.GetName().Name);
            await using var running = await registry.BuildAsync(registry.Validate().Composition!);
            await running.App.MapHoardModulesAsync(running.Lease);
            var result = await running.Lease.Lifecycle.StartAsync();
            Assert.Equal(repaired, result.Ready);
            Assert.Equal(repaired, running.Lease.Lifecycle.Snapshot.StartupAdmission);
            if (repaired)
            {
                Assert.IsType<ArtifactResult<ArtifactAdmission>.Success>(admission.Admission);
                Assert.Contains("initialize.before-root", controls.Observed);
                Assert.True(store.Ready);
            }
            else
            {
                var denied = Assert.IsType<ArtifactResult<ArtifactAdmission>.Failure>(admission.Admission);
                Assert.Equal(variant == "authority-identity" ? ArtifactFailureCode.Denied : ArtifactFailureCode.Unsupported, denied.Code);
                Assert.DoesNotContain("initialize.before-root", controls.Observed);
                Assert.False(Directory.Exists(directory.ArtifactRoot));
                Assert.False(store.Ready);
                Assert.Equal(0, registry.Probes["artifact"].Workers);
                Assert.Equal(0, registry.Probes["artifact"].Assessments);
                Assert.Equal(0, registry.Probes["artifact"].Requests);
                Safe(result.Diagnostics);
            }
            Inactive(registry.Probes["artifact-other"]);
            if (repaired)
            { await LifecycleTestHarness.Until(() => registry.Probes["metadata"].Workers == 1 && registry.Probes["artifact"].Workers == 1); }
            observation.Write(repaired ? "store-repair-admitted" : "store-denied", running.Lease, result);
            await running.DisposeAsync();
            Assert.True(running.Lease.StopResult!.Complete);
            Assert.Equal(ArtifactCleanupState.Released, Assert.IsType<ArtifactResult<ArtifactShutdown>.Success>(admission.Shutdown).Value.State);
            if (!observation.Write(repaired ? "store-repair-stopped" : "store-denial-stopped", running.Lease, result))
            {
                Observe($"CP-19/{variant}/repaired-{repaired}", registry, running.Lease);
                output.WriteLine($"CP-19/{variant}/repaired-{repaired}: store-before-root={controls.Observed.Count(point => point == "initialize.before-root")}; " +
                    $"store-admitted={controls.Observed.Count(point => point == "initialize.admitted")}; store-ready={(store.Ready ? 1 : 0)}; alternate-constructors=0");
            }
        }
    }

    private sealed class StoreAdmissionObservation(ITestOutputHelper output, string identity, Registry registry,
        OwnershipFixtures.ControlledAdmission admission)
    {
        private readonly ConformanceOriginalObservation? owner =
            ConformanceOriginalObservationOutput.WriteIfRequested(
                output, identity, "none", "original-owner", null, null, ("owner", registry));

        public bool Write(string stage, HoardServiceComposition lease, HoardStartResult start)
        {
            if (owner is null) { return false; }
            var fallback = registry.Probes["artifact-other"];
            ConformanceCompositionObservationOutput.Write(output, owner, stage,
                new Dictionary<string, int>(StringComparer.Ordinal)
                {
                    ["ready"] = lease.Lifecycle.Snapshot.Ready ? 1 : 0,
                    ["admission"] = lease.Lifecycle.Snapshot.StartupAdmission ? 1 : 0,
                    ["phaseFailures"] = start.Diagnostics.Count(item => item.RuleCode == "PhaseFailure"),
                    ["fallbackEffects"] = Effects(fallback),
                    ["workers"] = registry.Probes.Values.Sum(probe => probe.Workers),
                    ["stopComplete"] = lease.StopResult?.Complete == true ? 1 : 0,
                    ["rootDisposal"] = (int?)(lease.StopResult?.RootDisposal) ?? 6,
                    ["unsafeActivities"] = lease.StopResult?.UnsafeActivities.Length ?? 0,
                    ["storeBeforeRoot"] = admission.Controls.Observed.Count(point => point == "initialize.before-root"),
                    ["storeAdmitted"] = admission.Controls.Observed.Count(point => point == "initialize.admitted"),
                    ["storeReady"] = admission.Store.Ready ? 1 : 0
                });
            return true;
        }
    }
#endif
}
