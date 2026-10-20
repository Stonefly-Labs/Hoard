using System.Runtime.CompilerServices;

try
{
    Console.WriteLine(Caller.Invoke());
    return 0;
}
catch (MissingMethodException error)
{
    Console.Error.WriteLine(error.GetType().Name);
    return 1;
}

internal static class Caller
{
    [MethodImpl(MethodImplOptions.NoInlining)]
    internal static string Invoke() => BinaryContract.Api.Describe();
}
