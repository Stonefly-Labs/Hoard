using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Catalog;

namespace Hoard.Fixtures.Conformance.Consumer;

internal static class BindingAdmissionAssertions
{
    internal static async Task MetadataAsync(
        ConformanceBindingDeclaration declaration, ConformanceRunContext context)
    {
        CatalogDurability("metadata", "MP", ["memory", "sqlite"], "memory",
            ["MP-36", "MP-38", "MP-39", "MP-40", "MP-41", "MP-42", "MP-43", "MP-44", "MP-45"],
            "non-durable fixture");
        Assert.Equal("binding", (await Assert.ThrowsAsync<ArgumentNullException>(() =>
            ConformanceObservedMetadataSession.OpenAsync(null!, context, default).AsTask())).ParamName);
        Assert.Equal("binding", (await Assert.ThrowsAsync<ArgumentNullException>(() =>
            ConformanceObservedMetadataSession.OpenLegacyAsync(null!, context, default).AsTask())).ParamName);
        ConformanceFault[] required = [
            ConformanceFault.IndependentSnapshot, ConformanceFault.WriterContention,
            ConformanceFault.CommitAcknowledgement, ConformanceFault.PersistedCorruption,
            ConformanceFault.Capacity, ConformanceFault.SchemaState, ConformanceFault.LeaseBoundary,
            ConformanceFault.NativeNonCooperation, ConformanceFault.CleanupFailure];
        if (declaration.Capabilities.Contains("durable-local-process-crash"))
        { required = [.. required, ConformanceFault.BackupRestore]; }
        foreach (var incomplete in MissingHooks(declaration, required, "exclude:MP-21"))
        {
            var rejected = new RejectedMetadataBinding(incomplete);
            Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<ArgumentException>(() =>
                ConformanceObservedMetadataSession.OpenAsync(rejected, context, default).AsTask())).Message);
            Assert.Equal(0, rejected.FactoryCalls);
            Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<ArgumentException>(() =>
                ConformanceObservedMetadataSession.OpenLegacyAsync(rejected, context, default).AsTask())).Message);
            Assert.Equal(0, rejected.FactoryCalls);
        }
    }

    internal static async Task ArtifactsAsync(
        ConformanceBindingDeclaration declaration, ConformanceRunContext context)
    {
        CatalogDurability("artifacts", "AS", ["local", "object"], "object",
            ["AS-41", "AS-42", "AS-43", "AS-44"], "simulation: no durable restart");
        Assert.Equal("binding", (await Assert.ThrowsAsync<ArgumentNullException>(() =>
            ConformanceObservedArtifactSession.OpenAsync(null!, context, default).AsTask())).ParamName);
        ConformanceFault[] required = [
            ConformanceFault.PublicationBoundary, ConformanceFault.DirectVisibility,
            ConformanceFault.PayloadDamage, ConformanceFault.Capacity,
            ConformanceFault.NativeNonCooperation, ConformanceFault.CleanupFailure,
            ConformanceFault.GenerationBoundary, ConformanceFault.ReceiptBoundary,
            ConformanceFault.SourceNonCooperation, ConformanceFault.SinkNonCooperation];
        foreach (var incomplete in MissingHooks(declaration, required, "exclude:AS-15"))
        {
            var rejected = new RejectedArtifactBinding(incomplete);
            Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<ArgumentException>(() =>
                ConformanceObservedArtifactSession.OpenAsync(rejected, context, default).AsTask())).Message);
            Assert.Equal(0, rejected.FactoryCalls);
        }
    }

    private static void CatalogDurability(
        string profile, string prefix, string[] bindings, string nonDurableBinding,
        string[] exclusions, string rule)
    {
        var catalog = ConformanceCatalog.Expand(profile);
        Assert.Equal<string>(bindings.Order(StringComparer.Ordinal),
            catalog.Where(entry => entry.BindingId != "none").Select(entry => entry.BindingId)
                .Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal));
        foreach (var binding in bindings)
        {
            var rows = catalog.Where(entry => entry.BindingId == binding).ToArray();
            Assert.Equal<string>(Enumerable.Range(1, 48).Select(number => $"{prefix}-{number:00}"),
                rows.Select(entry => entry.CaseId).Order(StringComparer.Ordinal));
            Assert.All(rows, entry => Assert.Equal("none", entry.MatrixId));
        }
        foreach (var entry in catalog)
        {
            var excluded = entry.BindingId == nonDurableBinding
                && exclusions.Contains(entry.CaseId, StringComparer.Ordinal);
            Assert.Equal(excluded ? rule : null, entry.Exclusion);
        }
    }

    private static IEnumerable<ConformanceBindingDeclaration> MissingHooks(
        ConformanceBindingDeclaration declaration, IEnumerable<ConformanceFault> required, string logicalExclusion)
    {
        foreach (var missing in required)
        {
            foreach (var capabilities in new[] {
                declaration.Capabilities, declaration.Capabilities.Add(logicalExclusion) })
            {
                yield return new(declaration.BindingId, declaration.Category, declaration.PackageId,
                    declaration.PackageVersion, declaration.PackageSha256, capabilities,
                    declaration.Faults.Where(fault => fault != missing));
            }
        }
    }

    private sealed class RejectedMetadataBinding(
        ConformanceBindingDeclaration declaration) : IMetadataConformanceBinding
    {
        public ConformanceBindingDeclaration Declaration => declaration;
        public int FactoryCalls { get; private set; }

        public ValueTask<IMetadataConformanceSession> CreateSessionAsync(
            ConformanceRunContext context, CancellationToken cancellationToken)
        {
            FactoryCalls++;
            throw new InvalidOperationException("BindingInvalid");
        }

        public ValueTask<IMetadataConformanceSession> CreateLegacySessionAsync(
            ConformanceRunContext context, CancellationToken cancellationToken)
        {
            FactoryCalls++;
            throw new InvalidOperationException("BindingInvalid");
        }
    }

    private sealed class RejectedArtifactBinding(
        ConformanceBindingDeclaration declaration) : IArtifactConformanceBinding
    {
        public ConformanceBindingDeclaration Declaration => declaration;
        public int FactoryCalls { get; private set; }

        public ValueTask<IArtifactConformanceSession> CreateSessionAsync(
            ConformanceRunContext context, CancellationToken cancellationToken)
        {
            FactoryCalls++;
            throw new InvalidOperationException("BindingInvalid");
        }
    }
}
