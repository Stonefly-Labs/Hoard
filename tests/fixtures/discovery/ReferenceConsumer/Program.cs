using System.Text.Json;
using Hoard.Discovery.ReferenceConsumer;

using var buffer = new MemoryStream();
var input = Console.OpenStandardInput();
var chunk = new byte[8192];
while (true)
{
    var count = await input.ReadAsync(chunk);
    if (count == 0) { break; }
    if (buffer.Length + count > 4 * 1024 * 1024)
    { Console.Error.WriteLine("Discovery response exceeds its public bound."); return 1; }
    buffer.Write(chunk, 0, count);
}
var parsed = DiscoveryJsonReader.Read(buffer.ToArray());
if (!parsed.Compatible) { Console.Error.WriteLine(parsed.Code); return 1; }
Console.WriteLine(JsonSerializer.Serialize(PresentationProjector.Project(parsed.Observation!, false, new HashSet<string>())));
return 0;
