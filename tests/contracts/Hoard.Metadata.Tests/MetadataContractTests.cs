using System.Collections.Immutable;
using Hoard.Abstractions.Metadata;
using Hoard.Abstractions.Providers;

namespace Hoard.Metadata.Tests;

public sealed class MetadataContractTests
{
    [Fact]
    public void Existing_marker_stays_empty_and_operational_contracts_are_separate()
    {
        Assert.Empty(typeof(IMetadataProvider).GetMethods());
        Assert.False(typeof(IMetadataProvider).IsAssignableFrom(typeof(IMetadataStore)));
        Assert.Equal(5, typeof(IMetadataStore).GetMethods().Length);
        Assert.Equal(2, typeof(IMetadataSchemaAdministration).GetMethods().Length);
        Assert.True(typeof(IAsyncDisposable).IsAssignableFrom(typeof(IMetadataStore)));
    }

    [Fact]
    public void Read_groups_reject_uninitialized_empty_or_oversized_collections_before_copying()
    {
        var selector = new MetadataSelector.Registry(new MetadataId(Guid.NewGuid()));
        Assert.Single(new MetadataReadGroup([selector]).Selectors);
        Assert.Equal(64, new MetadataReadGroup(Enumerable.Repeat<MetadataSelector>(selector, 64).ToImmutableArray()).Selectors.Length);
        Assert.Throws<ArgumentException>(() => new MetadataReadGroup(default));
        Assert.Throws<ArgumentException>(() => new MetadataReadGroup([]));
        Assert.Throws<ArgumentException>(() => new MetadataReadGroup(Enumerable.Repeat<MetadataSelector>(selector, 65).ToImmutableArray()));
    }

    [Fact]
    public void Failure_cannot_carry_a_success_payload_or_render_injected_content()
    {
        MetadataResult<MetadataReadSnapshot> result = new MetadataResult<MetadataReadSnapshot>.Failure(
            MetadataFailureCode.Unavailable, MetadataPhase.Read, MetadataRetryDisposition.OperatorRecovery,
            new MetadataId(Guid.NewGuid()));
        Assert.IsType<MetadataResult<MetadataReadSnapshot>.Failure>(result);
        Assert.Null(result.GetType().GetProperty("Value"));
        Assert.DoesNotContain(MetadataTestData.Canary, result.ToString());
    }
}
