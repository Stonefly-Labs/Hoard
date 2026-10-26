using Hoard.Testing.Conformance.Bindings;

namespace Hoard.Fixtures.Conformance.Consumer;

internal static class BindingAdmissionAssertions
{
    internal static async Task MetadataAsync(
        ConformanceBindingDeclaration declaration, ConformanceRunContext context)
    {
        ConformanceFault[] required = [
            ConformanceFault.IndependentSnapshot, ConformanceFault.WriterContention,
            ConformanceFault.CommitAcknowledgement, ConformanceFault.PersistedCorruption,
            ConformanceFault.Capacity, ConformanceFault.SchemaState, ConformanceFault.LeaseBoundary,
            ConformanceFault.NativeNonCooperation, ConformanceFault.CleanupFailure];
        if (declaration.Capabilities.Contains("durable-local-process-crash"))
        { required = [.. required, ConformanceFault.BackupRestore]; }
        foreach (var missing in required)
        {
            var rejected = new RejectedMetadataBinding(Without(declaration, missing));
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
        ConformanceFault[] required = [
            ConformanceFault.PublicationBoundary, ConformanceFault.DirectVisibility,
            ConformanceFault.PayloadDamage, ConformanceFault.Capacity,
            ConformanceFault.NativeNonCooperation, ConformanceFault.CleanupFailure,
            ConformanceFault.GenerationBoundary, ConformanceFault.ReceiptBoundary,
            ConformanceFault.SourceNonCooperation, ConformanceFault.SinkNonCooperation];
        foreach (var missing in required)
        {
            var rejected = new RejectedArtifactBinding(Without(declaration, missing));
            Assert.Equal("BindingInvalid", (await Assert.ThrowsAsync<ArgumentException>(() =>
                ConformanceObservedArtifactSession.OpenAsync(rejected, context, default).AsTask())).Message);
            Assert.Equal(0, rejected.FactoryCalls);
        }
    }

    private static ConformanceBindingDeclaration Without(
        ConformanceBindingDeclaration declaration, ConformanceFault missing) =>
        new(declaration.BindingId, declaration.Category, declaration.PackageId, declaration.PackageVersion,
            declaration.PackageSha256, declaration.Capabilities, declaration.Faults.Where(fault => fault != missing));

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
