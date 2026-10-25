using Hoard.Testing.Conformance.Metadata;
using Xunit.Abstractions;
using static Hoard.Metadata.Tests.MetadataCases;

namespace Hoard.Metadata.Tests;

public sealed class MetadataIdentityTests(ITestOutputHelper output)
{
    [Fact]
    public async Task MP02_Registry_identity_is_exact_and_isolated()
    {
        await using var fixture = await OpenAsync();
        var authority = CommonAuthority(fixture);
        await MetadataIdentityAssertions.RegistryIsolationAsync(fixture.Store, authority, default);
        ObserveOriginal(output, fixture, authority, nameof(MetadataIdentityTests));
    }

    [Fact]
    public async Task MP03_Anonymous_and_authenticated_request_partitions_remain_separate()
    {
        await using var fixture = await OpenAsync();
        var authority = CommonAuthority(fixture);
        await MetadataIdentityAssertions.AuthorizationPartitionIsolationAsync(fixture.Store, authority, default);
        ObserveOriginal(output, fixture, authority, nameof(MetadataIdentityTests));
    }

    [Fact]
    public async Task MP04_Canonical_text_is_not_normalized_and_forbidden_credentials_are_rejected()
    {
        await using var fixture = await OpenAsync();
        await MetadataIdentityAssertions.CanonicalTextAndForbiddenValuesAsync(fixture.Store, default);
    }
}
