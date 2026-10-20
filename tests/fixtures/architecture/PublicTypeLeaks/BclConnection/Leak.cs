using System.Data.Common;

public class Leak
{
    public DbConnection? Connection { get; init; }
    public DbTransaction? Transaction { get; init; }
}
