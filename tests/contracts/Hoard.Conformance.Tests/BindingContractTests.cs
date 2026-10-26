using System.Collections.Immutable;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Storage;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Catalog;
using Hoard.Testing.Conformance.Diagnostics;
using Hoard.Testing.Conformance.Evidence;

namespace Hoard.Conformance.Tests;

public sealed class BindingContractTests
{
    [Fact]
    public async Task Observed_legacy_factory_uses_explicit_setup_without_case_id_routing()
    {
        var binding = new MetadataProbeBinding();
        var context = new ConformanceRunContext(Guid.NewGuid(), "arbitrary-case", TimeProvider.System,
            new UnusedResources(), new ConformanceEvidenceBuffer());
        await using var observed = await ConformanceObservedMetadataSession.OpenLegacyAsync(binding, context, default);
        Assert.Equal(0, binding.Creates);
        Assert.Equal(1, binding.LegacyCreates);
        Assert.Equal(0, binding.Session.StoreReads);
        Assert.Same(binding.Session.First, observed.Store);
        var origin = observed.CaptureOrigin();
        Assert.Equal("create", origin.FactoryOperation);
        Assert.Null(origin.ParentSessionId);
        Assert.Equal(context.CaseId, origin.CaseId);
        Assert.Equal(origin.Components["store"].InstanceId, origin.Components["schema"].InstanceId);
    }

    [Fact]
    public async Task Observed_artifact_sessions_pin_all_actual_roles_and_preserve_cleanup_ownership_on_capture_failure()
    {
        var binding = new ArtifactProbeBinding();
        var context = new ConformanceRunContext(Guid.NewGuid(), "runtime-origin", TimeProvider.System,
            new UnusedResources(), new ConformanceEvidenceBuffer());
        var observed = await ConformanceObservedArtifactSession.OpenAsync(binding, context, default);
        try
        {
            var lifetime = observed.Lifetime;
            Assert.Same(lifetime, observed.Lifetime);
            var origin = observed.CaptureOrigin();
            Assert.Equal(1, binding.Session.LifetimeReads);
            Assert.Equal<string>(["authority", "factory", "faults", "lifetime", "maintenance", "session", "store", "validator"],
                origin.Components.Keys);
            Assert.Equal(origin.Components["lifetime"].InstanceId, origin.Components["validator"].InstanceId);
            Assert.Equal(origin.Components["store"].InstanceId, origin.Components["authority"].InstanceId);
            await using var reopened = await observed.ReopenAsync(default);
            var reopenedOrigin = Assert.IsType<ConformanceObservedArtifactSession>(reopened).CaptureOrigin();
            Assert.Equal(origin.SessionId, reopenedOrigin.ParentSessionId);
            binding.Session.First.SupportedFaults = [];
            Assert.Equal("BindingInvalid", Assert.Throws<ArgumentException>(() => observed.CaptureOrigin()).Message);
        }
        finally { await observed.DisposeAsync(); }
        Assert.True(binding.Session.Disposed);
        var throwing = new ArtifactProbeBinding();
        throwing.Session.ThrowOnLifetime = true;
        var owned = await ConformanceObservedArtifactSession.OpenAsync(throwing, context, default);
        try
        {
            Assert.Equal("UnknownDiagnostic",
                Assert.Throws<InvalidOperationException>(() => owned.CaptureOrigin()).Message);
        }
        finally { await owned.DisposeAsync(); }
        Assert.True(throwing.Session.Disposed);
    }

    [Fact]
    public async Task Observed_metadata_sessions_pin_factory_results_and_actual_component_instances()
    {
        var binding = new MetadataProbeBinding();
        var context = new ConformanceRunContext(Guid.NewGuid(), "runtime-origin", TimeProvider.System,
            new UnusedResources(), new ConformanceEvidenceBuffer());
        await using var observed = await ConformanceObservedMetadataSession.OpenAsync(binding, context, default);
        Assert.Equal(0, binding.Session.StoreReads);
        var first = observed.Store;
        Assert.Same(first, observed.Store);
        Assert.Equal(1, binding.Session.StoreReads);
        await observed.Store.DisposeAsync();
        Assert.Equal(1, binding.Session.First.DisposeCount);
        Assert.Equal(0, binding.Session.Second.DisposeCount);
        var origin = observed.CaptureOrigin();
        Assert.Equal(1, binding.Creates);
        Assert.Equal(context.RunId, origin.RunId);
        Assert.Equal(context.CaseId, origin.CaseId);
        Assert.Equal(Hash(ConformanceBindingSnapshot.Capture(binding.Declaration).AsSpan()), origin.DescriptorSha256);
        Assert.Equal<string>(["authority", "factory", "faults", "schema", "session", "store"], origin.Components.Keys);
        Assert.Equal(origin.Components["store"].InstanceId, origin.Components["schema"].InstanceId);
        Assert.Equal(origin.Components["store"].InstanceId, origin.Components["authority"].InstanceId);
        Assert.Equal(origin.Components["store"].InstanceId, origin.Components["faults"].InstanceId);
        Assert.NotEqual(origin.Components["store"].InstanceId, origin.Components["factory"].InstanceId);
        Assert.Equal(ConformanceLoadedAssembly.Capture(first).TypeSha256,
            origin.Components["store"].Assembly.TypeSha256);
        Assert.Equal(origin.Components["store"].InstanceId, observed.CaptureOrigin().Components["store"].InstanceId);
        var projection = JsonSerializer.Serialize(origin,
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
        Assert.DoesNotContain(typeof(MetadataProbe).FullName!, projection, StringComparison.Ordinal);
        Assert.DoesNotContain(typeof(MetadataProbe).Assembly.Location, projection, StringComparison.Ordinal);
        Assert.DoesNotContain("private-canary", projection, StringComparison.Ordinal);
        var packets = ConformanceSessionOriginOutput.Render(origin);
        Assert.NotEmpty(packets);
        Assert.All(packets, packet =>
        {
            Assert.InRange(packet.Length, 1, 1024);
            Assert.DoesNotContain(typeof(MetadataProbe).FullName!, packet, StringComparison.Ordinal);
        });
        await using var reopened = await observed.ReopenAsync(default);
        var reopenedOrigin = Assert.IsType<ConformanceObservedMetadataSession>(reopened).CaptureOrigin();
        Assert.Equal(origin.SessionId, reopenedOrigin.ParentSessionId);
        Assert.Equal("reopen", reopenedOrigin.FactoryOperation);
        Assert.NotEqual(origin.SessionId, reopenedOrigin.SessionId);
        Assert.Equal(origin.Components["factory"].InstanceId, reopenedOrigin.Components["factory"].InstanceId);
    }

    [Fact]
    public async Task Observed_metadata_origin_rejects_changed_declarations_and_missing_actual_fault_hooks()
    {
        var context = new ConformanceRunContext(Guid.NewGuid(), "runtime-origin", TimeProvider.System,
            new UnusedResources(), new ConformanceEvidenceBuffer());
        var binding = new MetadataProbeBinding();
        await using var observed = await ConformanceObservedMetadataSession.OpenAsync(binding, context, default);
        binding.Declaration = new("binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0",
            new string('a', 64), ["common-logical", "changed"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
        Assert.Equal("InputChanged", Assert.Throws<InvalidOperationException>(() => observed.CaptureOrigin()).Message);
        var missing = new MetadataProbeBinding();
        missing.Session.First.SupportedFaults = [];
        await using var invalid = await ConformanceObservedMetadataSession.OpenAsync(missing, context, default);
        Assert.Equal("BindingInvalid", Assert.Throws<ArgumentException>(() => invalid.CaptureOrigin()).Message);
        var durable = new MetadataProbeBinding
        {
            Declaration = new("binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0", new string('a', 64),
                ["durable-local-process-crash"],
                [.. ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata), ConformanceFault.BackupRestore])
        };
        await using var missingBackup = await ConformanceObservedMetadataSession.OpenAsync(durable, context, default);
        Assert.Equal("BindingInvalid", Assert.Throws<ArgumentException>(() => missingBackup.CaptureOrigin()).Message);
    }

    [Fact]
    public void Loaded_component_capture_observes_instance_bytes_and_type_not_interface_or_declaration_labels()
    {
        IConformanceBinding first = new ObservedBinding();
        IConformanceBinding second = new OtherObservedBinding();
        var observed = ConformanceLoadedAssembly.Capture(first);
        var other = ConformanceLoadedAssembly.Capture(second);
        var assembly = typeof(ObservedBinding).Assembly;
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(assembly.Location))),
            observed.AssemblySha256);
        Assert.Equal(assembly.ManifestModule.ModuleVersionId, observed.ModuleVersionId);
        Assert.Equal(assembly.GetName().Name, observed.AssemblyName);
        Assert.Equal(assembly.GetName().Version!.ToString(), observed.AssemblyVersion);
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(typeof(ObservedBinding).FullName!))),
            observed.TypeSha256);
        Assert.Equal(observed.AssemblySha256, other.AssemblySha256);
        Assert.NotEqual(observed.TypeSha256, other.TypeSha256);
        Assert.NotEqual(first.Declaration.PackageSha256, observed.AssemblySha256);
        Assert.NotEqual(typeof(IConformanceBinding).Assembly.ManifestModule.ModuleVersionId, observed.ModuleVersionId);
    }

    [Fact]
    public void Loaded_component_projection_is_closed_and_never_renders_provider_objects_or_private_paths()
    {
        IConformanceBinding binding = new ObservedBinding();
        var observed = ConformanceLoadedAssembly.Capture(binding);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(observed,
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
        using var document = JsonDocument.Parse(bytes);
        Assert.Equal<string>(["assemblyName", "assemblyVersion", "moduleVersionId", "assemblySha256", "typeSha256"],
            document.RootElement.EnumerateObject().Select(property => property.Name));
        var text = Encoding.UTF8.GetString(bytes);
        Assert.DoesNotContain("private-canary", text, StringComparison.Ordinal);
        Assert.DoesNotContain(typeof(ObservedBinding).Assembly.Location, text, StringComparison.Ordinal);
        Assert.DoesNotContain(typeof(ObservedBinding).FullName!, text, StringComparison.Ordinal);
    }

    [Fact]
    public void Binding_snapshots_capture_closed_actual_declarations_without_outcome_labels()
    {
        var declaration = Declare(ConformanceCategory.Metadata,
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
        var snapshot = ConformanceBindingSnapshot.Capture(declaration);
        using var document = JsonDocument.Parse(snapshot.AsMemory());
        var root = document.RootElement;
        Assert.Equal<string>(
            ["schemaVersion", "bindingId", "category", "packageId", "packageVersion",
             "packageSha256", "capabilities", "faults"],
            root.EnumerateObject().Select(property => property.Name));
        Assert.Equal(1, root.GetProperty("schemaVersion").GetInt32());
        Assert.Equal(declaration.BindingId, root.GetProperty("bindingId").GetString());
        Assert.Equal("metadata", root.GetProperty("category").GetString());
        Assert.Equal(declaration.PackageId, root.GetProperty("packageId").GetString());
        Assert.Equal(declaration.PackageVersion, root.GetProperty("packageVersion").GetString());
        Assert.Equal(declaration.PackageSha256, root.GetProperty("packageSha256").GetString());
        Assert.Equal(declaration.Capabilities,
            root.GetProperty("capabilities").EnumerateArray().Select(value => value.GetString()));
        Assert.Equal(declaration.Faults.Select(fault => fault.ToString()),
            root.GetProperty("faults").EnumerateArray().Select(value => value.GetString()));
        Assert.Equal<byte>(snapshot, ConformanceBindingSnapshot.Capture(declaration));
    }

    [Fact]
    public void Binding_snapshots_reject_missing_faults_before_emitting_input_bytes()
    {
        foreach (var category in new[] { ConformanceCategory.Metadata, ConformanceCategory.Artifacts })
        {
            var faults = ConformanceBindingAdmission.RequiredFaults(category);
            foreach (var missing in faults)
            {
                var declaration = Declare(category, faults.Where(fault => fault != missing));
                var error = Assert.Throws<ArgumentException>(() => ConformanceBindingSnapshot.Capture(declaration));
                Assert.Equal("BindingInvalid", error.Message);
            }
            Assert.False(ConformanceBindingSnapshot.Capture(Declare(category, faults)).IsEmpty);
        }
    }

    [Theory]
    [InlineData(ConformanceCategory.Metadata)]
    [InlineData(ConformanceCategory.Artifacts)]
    public void Missing_mandatory_faults_cannot_reduce_the_common_agreement(ConformanceCategory category)
    {
        var faults = ConformanceBindingAdmission.RequiredFaults(category);
        foreach (var missing in faults)
        {
            var declaration = Declare(category, faults.Where(fault => fault != missing));
            var failure = Assert.Throws<ArgumentException>(() => ConformanceBindingAdmission.Validate(declaration, category));
            Assert.Equal("BindingInvalid", failure.Message);
        }
        ConformanceBindingAdmission.Validate(Declare(category, faults), category);
    }

    [Fact]
    public void Admission_copies_declarations_and_never_accepts_provider_selected_exclusions()
    {
        var capabilities = new List<string> { "common-logical" };
        var faults = ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata).ToList();
        var declaration = new ConformanceBindingDeclaration(
            "binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0",
            new string('a', 64), capabilities, faults);
        capabilities.Clear();
        faults.Clear();
        Assert.Equal<string>(["common-logical"], declaration.Capabilities);
        ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Metadata);
        Assert.Throws<ArgumentException>(() => ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Artifacts));
        var expected = ConformanceCatalog.Expand("metadata");
        var mandatory = expected.Where(entry => entry.BindingId == "memory"
            && entry.CaseId.StartsWith("MP-", StringComparison.Ordinal) && entry.Exclusion is null);
        Assert.All(mandatory, entry => Assert.NotEmpty(entry.Witnesses.Concat(entry.Controls)));
        Assert.DoesNotContain(mandatory, entry => entry.CaseId == "MP-36");
        Assert.Contains(mandatory, entry => entry.CaseId == "MP-37");
        Assert.Contains(mandatory, entry => entry.CaseId == "MP-48");
    }

    [Fact]
    public void Durable_metadata_requires_backup_controls_in_addition_to_logical_faults()
    {
        var declaration = new ConformanceBindingDeclaration(
            "binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0", new string('a', 64),
            ["common-logical", "durable-local-process-crash"],
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
        Assert.Throws<ArgumentException>(() => ConformanceBindingAdmission.Validate(declaration, ConformanceCategory.Metadata));
        var repaired = new ConformanceBindingDeclaration(
            "binding", ConformanceCategory.Metadata, "Hoard.Fixture", "0.1.0", new string('a', 64),
            ["common-logical", "durable-local-process-crash"],
            declaration.Faults.Add(ConformanceFault.BackupRestore));
        ConformanceBindingAdmission.Validate(repaired, ConformanceCategory.Metadata);
    }

    [Fact]
    public void Released_observations_cannot_stand_in_for_retained_ownership()
    {
        var resources = new List<string> { "owned-resource" };
        var retained = new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, resources,
            ConformanceDiagnosticCode.CleanupIncomplete);
        resources.Clear();
        Assert.Equal<string>(["owned-resource"], retained.ResourceIds);
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, []));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, ["same", "same"]));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Retained, ["owned"]));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Released, ["owned"]));
        Assert.Throws<ArgumentException>(() => new ConformanceCleanupObservation(ConformanceOwnershipState.Released, [],
            ConformanceDiagnosticCode.CleanupIncomplete));
        Assert.Equal(ConformanceDiagnosticCode.CleanupIncomplete, retained.Reason);
    }

    [Fact]
    public void Fault_observations_reject_private_paths_invalid_counts_and_unknown_states()
    {
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            ConformanceFault.Capacity, "/private/synthetic-canary", 0, ConformanceOwnershipState.Active));
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            (ConformanceFault)int.MaxValue, "capacity", 0, ConformanceOwnershipState.Active));
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", -1, ConformanceOwnershipState.Active));
        Assert.Throws<ArgumentException>(() => new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", 0, (ConformanceOwnershipState)int.MaxValue));
    }

    [Fact]
    public void Corruption_requests_reject_missing_subjects_and_unknown_faults_at_admission()
    {
        var selector = new MetadataSelector.Registry(default!);
        var ticket = new MetadataOperationTicket(default!, default!, default!, default!);
        Action[] invalid =
        [
            () => _ = new MetadataCorruptionRequest.Record(null!, MetadataRecordCorruption.NullLabel),
            () => _ = new MetadataCorruptionRequest.Record(selector, (MetadataRecordCorruption)int.MaxValue),
            () => _ = new MetadataCorruptionRequest.Operation(null!, MetadataOperationCorruption.NullTarget, ticket),
            () => _ = new MetadataCorruptionRequest.Operation(ticket, (MetadataOperationCorruption)int.MaxValue, ticket),
            () => _ = new MetadataCorruptionRequest.Operation(ticket, MetadataOperationCorruption.MismatchedTicket, null!)
        ];
        foreach (var create in invalid)
        {
            Assert.Equal("BindingInvalid", Assert.Throws<ArgumentException>(create).Message);
        }
    }

    [Fact]
    public async Task Evidence_buffer_preserves_observation_order_without_mutable_snapshots()
    {
        var buffer = new ConformanceEvidenceBuffer();
        var first = new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", 1, ConformanceOwnershipState.Active);
        await buffer.ObserveAsync(first, default);
        var snapshot = buffer.Snapshot();
        var second = new ConformanceFaultObservation(
            ConformanceFault.CleanupFailure, "cleanup", 2, ConformanceOwnershipState.Retained);
        await buffer.ObserveAsync(second, default);
        Assert.Equal<ConformanceFaultObservation>([first], snapshot);
        Assert.Equal<ConformanceFaultObservation>([first, second], buffer.Snapshot());
    }

    [Fact]
    public async Task Evidence_buffer_rejects_cancellation_and_overflow_without_losing_prior_observations()
    {
        var buffer = new ConformanceEvidenceBuffer();
        var observation = new ConformanceFaultObservation(
            ConformanceFault.Capacity, "capacity", 1, ConformanceOwnershipState.Active);
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(async () =>
            await buffer.ObserveAsync(observation, cancelled.Token));
        Assert.Empty(buffer.Snapshot());
        for (var number = 0; number < 10_000; number++)
        {
            await buffer.ObserveAsync(observation, default);
        }
        var failure = await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            await buffer.ObserveAsync(observation, default));
        Assert.Equal("OutputLimitExceeded", failure.Message);
        Assert.Equal(10_000, buffer.Snapshot().Length);
        Assert.All(buffer.Snapshot(), observed => Assert.Equal(observation, observed));
    }

    [Fact]
    public void Catalog_exclusion_cannot_be_fabricated_as_a_runtime_execution()
    {
        var expected = ConformanceCatalog.Expand("metadata").First(entry => !entry.Witnesses.IsEmpty);
        Assert.Throws<ArgumentException>(() => new ConformanceRuntimeWitness(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), expected, expected.Witnesses[0],
            new string('a', 64), new string('b', 64), new string('c', 64),
            TimeSpan.Zero, TimeSpan.FromSeconds(1), ConformanceWitnessStatus.NotApplicable,
            new string('d', 64)));
    }

    [Fact]
    public async Task Diagnostic_projection_accepts_only_closed_codes_and_numeric_measurements()
    {
        await using var output = new MemoryStream();
        await Assert.ThrowsAsync<ArgumentException>(async () =>
            await ConformanceDiagnostic.WriteAsync(output, (ConformanceDiagnosticCode)int.MaxValue, 1, default));
        Assert.Equal(0, output.Length);
        await ConformanceDiagnostic.WriteAsync(output, ConformanceDiagnosticCode.CleanupIncomplete, 1, default);
        Assert.Equal("{\"event\":\"control\",\"code\":\"CleanupIncomplete\",\"value\":1}\n",
            System.Text.Encoding.UTF8.GetString(output.ToArray()));
    }

    [Fact]
    public void Corruption_observations_cannot_export_private_values_as_fingerprints()
    {
        foreach (var input in new[] { "/private/synthetic-canary", new string('A', 64), new string('a', 65), "" })
        {
            var failure = Assert.Throws<ArgumentException>(() => new ConformanceStateFingerprint(input));
            Assert.Equal("BindingInvalid", failure.Message);
        }
        Assert.Equal(new ConformanceStateFingerprint(new string('a', 64)), new ConformanceStateFingerprint(new string('a', 64)));
    }

    private static ConformanceBindingDeclaration Declare(
        ConformanceCategory category, IEnumerable<ConformanceFault> faults) =>
        new("binding", category, "Hoard.Fixture", "0.1.0", new string('a', 64), ["common-logical"], faults);

    private class ObservedBinding : IConformanceBinding
    {
        public ConformanceBindingDeclaration Declaration => Declare(ConformanceCategory.Metadata,
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
        public override string ToString() => throw new InvalidOperationException("private-canary");
    }

    private sealed class OtherObservedBinding : ObservedBinding;

    private static string Hash(ReadOnlySpan<byte> bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    internal static async ValueTask<ConformanceSessionOrigin> CaptureMetadataOriginAsync(
        Guid runId, string caseId, ConformanceBindingDeclaration? declaration = null)
    {
        var binding = new MetadataProbeBinding();
        if (declaration is not null) { binding.Declaration = declaration; }
        var context = new ConformanceRunContext(runId, caseId, TimeProvider.System,
            new UnusedResources(), new ConformanceEvidenceBuffer());
        await using var observed = await ConformanceObservedMetadataSession.OpenAsync(binding, context, default);
        return observed.CaptureOrigin();
    }

    private sealed class MetadataProbeBinding : IMetadataConformanceBinding
    {
        public ConformanceBindingDeclaration Declaration { get; set; } = Declare(ConformanceCategory.Metadata,
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata));
        internal MetadataProbeSession Session { get; } = new();
        internal int Creates { get; private set; }
        internal int LegacyCreates { get; private set; }
        public ValueTask<IMetadataConformanceSession> CreateSessionAsync(ConformanceRunContext context, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            Creates++;
            return ValueTask.FromResult<IMetadataConformanceSession>(Session);
        }
        public ValueTask<IMetadataConformanceSession> CreateLegacySessionAsync(ConformanceRunContext context, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            LegacyCreates++;
            return ValueTask.FromResult<IMetadataConformanceSession>(Session);
        }
    }

    private sealed class MetadataProbeSession : IMetadataConformanceSession
    {
        internal MetadataProbe First { get; } = new();
        internal MetadataProbe Second { get; } = new();
        internal int StoreReads { get; private set; }
        public IMetadataStore Store => ++StoreReads == 1 ? First : Second;
        public IMetadataSchemaAdministration Schema => First;
        public IMetadataConformanceAuthority Authority => First;
        public IMetadataConformanceFaultDriver Faults => First;
        public ValueTask<IMetadataConformanceSession> ReopenAsync(CancellationToken token) =>
            ValueTask.FromResult<IMetadataConformanceSession>(new MetadataProbeSession());
        public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken token) =>
            ValueTask.FromResult(new ConformanceCleanupObservation(ConformanceOwnershipState.Released, []));
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }

    private sealed class MetadataProbe : IMetadataStore, IMetadataSchemaAdministration,
        IMetadataConformanceAuthority, IMetadataConformanceFaultDriver
    {
        public override bool Equals(object? other) => throw new InvalidOperationException("private-canary");
        public override int GetHashCode() => throw new InvalidOperationException("private-canary");
        public override string ToString() => throw new InvalidOperationException("private-canary");
        internal int DisposeCount { get; private set; }
        public ImmutableArray<ConformanceFault> SupportedFaults { get; set; } =
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Metadata);
        public ValueTask DisposeAsync() { DisposeCount++; return ValueTask.CompletedTask; }
        public ValueTask<MetadataResult<MetadataOperationTicket>> ReserveOperationAsync(MetadataCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataReadSnapshot>> ReadAsync(MetadataReadGroup r, MetadataCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataPage>> ReadPageAsync(MetadataPageQuery r, MetadataCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataCommitReceipt>> CommitAsync(MetadataMutationBatch r, MetadataCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataResolution>> ReconcileAsync(MetadataOperationTicket r, MetadataCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataSchemaInspection>> InspectAsync(MetadataAdministrationOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataSchemaAdmission>> PrepareAsync(MetadataSchemaRequest r, MetadataAdministrationOptions o, CancellationToken t) => throw new NotSupportedException();
        public MetadataArtifactEvidence Register(ArtifactDigest d, long l) => throw new NotSupportedException();
        public int Acquisitions => throw new NotSupportedException();
        public int ActiveGuards => throw new NotSupportedException();
        public void Revoke(MetadataArtifactEvidence e) => throw new NotSupportedException();
        public ValueTask<MetadataResult<IMetadataPublicationGuard>> AcquireAsync(MetadataArtifactEvidence e, MetadataCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask ArmAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public ValueTask WaitForBoundaryAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public ValueTask ReleaseAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ConformanceFaultObservation> ObserveAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<IMetadataCorruptionScope> CorruptAsync(MetadataCorruptionRequest r, CancellationToken t) => throw new NotSupportedException();
        public ValueTask RestoreCorruptionsAsync(CancellationToken t) => throw new NotSupportedException();
        public MetadataFaultCounters Counters => throw new NotSupportedException();
        public ValueTask<ConformanceStateFingerprint> ObserveStateAsync(CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataContinuation> CorruptContinuationAsync(MetadataContinuation c,
            MetadataContinuationComponent p, MetadataContinuationCorruption d, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<IAsyncDisposable> ObserveBoundaryAsync(MetadataObservationPoint p, Func<ValueTask> o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataReadSnapshot>> ObserveIndependentSnapshotAsync(MetadataReadGroup r, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<IAsyncDisposable> HoldWriterAsync(CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataId>> FillLedgerAsync(CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataId>> CorruptRecordAsync(MetadataSelector s, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataId>> SetLeaseGenerationAsync(CanonicalText r, long g, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataId>> SetFutureSchemaAsync(CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataResult<MetadataId>> CreateUnrecognizedLayoutAsync(bool p, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<MetadataRecoveryPoint> AuthorizeUpgradeAsync(CancellationToken t) => throw new NotSupportedException();
        public ValueTask AwaitSettlementAsync(CancellationToken t) => throw new NotSupportedException();
    }

    private sealed class UnusedResources : IConformanceResourceAllocator
    {
        public ValueTask<ConformanceOwnedDirectory> AllocateDirectoryAsync(CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ConformanceCleanupObservation> ReleaseAsync(ConformanceOwnedDirectory r, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ConformanceCleanupObservation> ReleaseAsync(ConformanceOwnedDirectory r, Task s, CancellationToken t) => throw new NotSupportedException();
    }

    private sealed class ArtifactProbeBinding : IArtifactConformanceBinding
    {
        public ConformanceBindingDeclaration Declaration => Declare(ConformanceCategory.Artifacts,
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Artifacts));
        internal ArtifactProbeSession Session { get; } = new();
        public ValueTask<IArtifactConformanceSession> CreateSessionAsync(ConformanceRunContext context, CancellationToken token) =>
            ValueTask.FromResult<IArtifactConformanceSession>(Session);
    }

    private sealed class ArtifactProbeSession : IArtifactConformanceSession
    {
        internal ArtifactProbe First { get; } = new();
        private readonly ArtifactProbe second = new();
        internal int LifetimeReads { get; private set; }
        internal bool Disposed { get; private set; }
        internal bool ThrowOnLifetime { get; set; }
        public IArtifactStore Store => First;
        public IArtifactEvidenceValidator Validator => First;
        public IArtifactMaintenance Maintenance => First;
        public IArtifactStoreLifetime Lifetime => ThrowOnLifetime
            ? throw new InvalidOperationException("UnknownDiagnostic") : ++LifetimeReads == 1 ? First : second;
        public IArtifactCoordinationAuthority Authority => First;
        public ArtifactStoreIdentity Identity { get; } = new("synthetic-probe", Guid.NewGuid(), Guid.NewGuid());
        public IArtifactConformanceFaultDriver Faults => First;
        public ValueTask<IArtifactConformanceSession> ReopenAsync(CancellationToken token) =>
            ValueTask.FromResult<IArtifactConformanceSession>(new ArtifactProbeSession());
        public ValueTask<ConformanceCleanupObservation> ObserveCleanupAsync(CancellationToken token) =>
            ValueTask.FromResult(new ConformanceCleanupObservation(ConformanceOwnershipState.Released, []));
        public ValueTask DisposeAsync() { Disposed = true; return ValueTask.CompletedTask; }
    }

    private sealed class ArtifactProbe : IArtifactStore, IArtifactEvidenceValidator, IArtifactMaintenance,
        IArtifactStoreLifetime, IArtifactCoordinationAuthority, IArtifactConformanceFaultDriver
    {
        public ImmutableArray<ConformanceFault> SupportedFaults { get; set; } =
            ConformanceBindingAdmission.RequiredFaults(ConformanceCategory.Artifacts);
        public ArtifactCapabilities Capabilities => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveWriteAsync(ArtifactWriteIntent i, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactOperationTicket>> ReserveDeleteAsync(ArtifactDeleteIntent i, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactStagedWrite>> StageAsync(ArtifactOperationTicket i, Stream s, ArtifactTransferOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactStagingOwner>> RenewAsync(ArtifactStagingOwner i, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactMutationReceipt>> CommitAsync(ArtifactStagedWrite i, ArtifactTransferOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<IArtifactReadSession>> OpenReadAsync(ArtifactReadRequest i, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactMutationReceipt>> DeleteAsync(ArtifactOperationTicket i, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactResolution>> ReconcileAsync(ArtifactOperationTicket i, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactCleanupReport>> AbandonAsync(ArtifactStagingOwner i, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactStamp>> ValidateAsync(ArtifactCommitEvidence e, IArtifactProtectionGuard p, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactRecoveryPage>> ObserveAsync(ArtifactRecoveryQuery q, ArtifactMaintenanceOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactCleanupReport>> CleanupAsync(ArtifactCleanupRequest r, ArtifactMaintenanceOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactAdmission>> InitializeAsync(ArtifactInitialization r, ArtifactMaintenanceOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<ArtifactShutdown>> StopAsync(ArtifactCleanupOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<IArtifactProtectionGuard>> AcquireAsync(ArtifactProtectionRequest r, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ArtifactResult<IArtifactProtectionGuard>> RetainAsync(IArtifactProtectionGuard p, ArtifactProtectionRequest r, ArtifactCallOptions o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask ArmAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public ValueTask WaitForBoundaryAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public ValueTask ReleaseAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<ConformanceFaultObservation> ObserveAsync(ConformanceFault f, CancellationToken t) => throw new NotSupportedException();
        public IArtifactBorrowedStream BorrowedSource => throw new NotSupportedException();
        public int WaitingAuthorityAdmissions => throw new NotSupportedException();
        public IArtifactBorrowedStream BorrowedDestination => throw new NotSupportedException();
        public ValueTask<IAsyncDisposable> ObserveBoundaryAsync(ArtifactObservationPoint p, Func<ValueTask> o, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<IArtifactFaultRegistration> InjectPublicationAcknowledgmentLossAsync(CancellationToken t) => throw new NotSupportedException();
        public ValueTask DamagePayloadAsync(ArtifactStamp stamp, bool truncate, CancellationToken t) => throw new NotSupportedException();
        public ValueTask<byte[]> CapturePayloadAsync(ArtifactStamp stamp, int maximumBytes, CancellationToken t) => throw new NotSupportedException();
        public ValueTask ReplacePayloadAsync(ArtifactStamp stamp, ReadOnlyMemory<byte> payload, CancellationToken t) => throw new NotSupportedException();
        public ValueTask RemovePayloadAsync(ArtifactStamp stamp, CancellationToken t) => throw new NotSupportedException();
        public ValueTask AwaitSettlementAsync(CancellationToken t) => throw new NotSupportedException();
    }
}
