using System.Security.Cryptography;
using Hoard.Abstractions.Metadata;
using Hoard.Fixtures.Conformance.Consumer;
using Hoard.Fixtures.Conformance.Contributor;
using Hoard.Testing.Conformance.Bindings;
using Hoard.Testing.Conformance.Metadata;

namespace Hoard.Conformance.Tests;

public sealed class ContributorJourneyTests
{
    [Fact]
    public async Task Good_faulty_and_corrected_packages_use_the_same_common_assertion_and_provider()
    {
        var unchanged = Images();
        foreach (var faulty in new[] { false, true, false })
        {
            await using var resources = new SqliteBindingTests.RecordingDirectories();
            var clock = new MetadataConformanceClock(new(1_800_000_000_000));
            var context = new ConformanceRunContext(Guid.NewGuid(), "contributor-journey", clock,
                resources, new ConformanceEvidenceBuffer());
            var binding = new ForwardingMetadataBinding(new string('a', 64), faulty);
            ConformanceBindingAdmission.Validate(binding.Declaration, ConformanceCategory.Metadata);
            Assert.Contains("forwarding-example", binding.Declaration.Capabilities);
            Assert.Contains("non-durable", binding.Declaration.Capabilities);
            Assert.DoesNotContain("durable-local-process-crash", binding.Declaration.Capabilities);
            await using (var session = await binding.CreateSessionAsync(context, default))
            {
                Assert.IsType<MetadataResult<MetadataSchemaAdmission>.Success>(
                    await session.Schema.PrepareAsync(new MetadataSchemaRequest.CreateIfEmpty(), new(), default));
                if (faulty)
                {
                    var error = await Assert.ThrowsAsync<Xunit.Sdk.IsTypeException>(
                        () => MetadataTimeAssertions.TicketExpiryAndRollbackAsync(session.Store, clock, default));
                    Assert.Contains(nameof(MetadataTimeAssertions.TicketExpiryAndRollbackAsync), error.StackTrace);
                }
                else
                {
                    await MetadataTimeAssertions.TicketExpiryAndRollbackAsync(session.Store, clock, default);
                }
            }
            Assert.Equal(unchanged, Images());
        }
    }

    [Fact]
    public async Task Forwarding_preserves_legacy_reopen_and_fault_ownership()
    {
        await using var resources = new SqliteBindingTests.RecordingDirectories();
        var context = new ConformanceRunContext(Guid.NewGuid(), "contributor-upgrade",
            new MetadataConformanceClock(new(1_800_000_000_000)), resources, new ConformanceEvidenceBuffer());
        var binding = new ForwardingMetadataBinding(new string('a', 64));
        Assert.Throws<ArgumentException>(() =>
            ConformanceBindingAdmission.Validate(binding.Declaration, ConformanceCategory.Artifacts));
        await using var session = await binding.CreateLegacySessionAsync(context, default);
        await MetadataSchemaAssertions.UpgradeAsync(session, default);
    }

    private static string[] Images() => new[]
    {
        typeof(IMetadataStore).Assembly,
        typeof(MetadataTimeAssertions).Assembly,
        typeof(Hoard.Fixtures.Conformance.Bindings.Memory.MemoryBinding).Assembly,
        typeof(Hoard.Fixtures.Metadata.Memory.MemoryMetadataStore).Assembly,
        typeof(ForwardingMetadataBinding).Assembly,
        typeof(ContributorJourneyTests).Assembly
    }.Select(assembly => Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(assembly.Location)))).ToArray();
}
