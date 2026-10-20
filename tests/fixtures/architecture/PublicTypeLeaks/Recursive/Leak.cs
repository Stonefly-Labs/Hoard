using FixtureSdk;

[Private(typeof(PrivateModel))]
public class Leak<T> : PrivateModel where T : IPrivateConstraint
{
    public Dictionary<string, List<PrivateModel[]>> Models { get; } = [];
    public event Action<PrivateModel>? Changed;
    public PrivateModel Echo(PrivateModel value)
    {
        Changed?.Invoke(value);
        return value;
    }
}
