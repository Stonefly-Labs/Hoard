using System.Data.Common;
using Hoard.Abstractions.Metadata;
using Microsoft.Data.Sqlite;

namespace Hoard.Fixtures.Metadata.BoundaryLeak;

public sealed class LeakingMetadataContract
{
    public SqliteConnection? Driver { get; init; }
    public Func<Task<IReadOnlyList<IQueryable<MetadataRegistry>>>>? DeferredQuery { get; init; }
    public DbTransaction? Transaction { get; init; }
}
