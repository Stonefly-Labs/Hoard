using System.Net;
using System.Text.Json;
using Hoard.Hosting.Lifecycle;
using Microsoft.AspNetCore.TestHost;

namespace Hoard.Composition.Tests;

public sealed class DiscoveryWireContractTests
{
    internal static string Root => Path.GetFullPath("../../../../../..", AppContext.BaseDirectory);

    [Fact]
    public async Task Serialized_data_description_problems_and_method_rules_match_the_normative_contract()
    {
        LifecycleFixtures.Reset();
        DiscoveryFixtures.Map();
        var (app, lease) = await DiscoveryAuthorizationTests.HttpFixture();
        await using (lease)
        {
            await app.StartAsync();
            using var client = app.GetTestClient();
            client.DefaultRequestHeaders.Add("X-Fixture-Identity", "read");
            var normative = await File.ReadAllBytesAsync(Path.Combine(Root, "specs/004-module-discovery/contracts/openapi.json"));
            Assert.Equal(normative, await client.GetByteArrayAsync("/api/v1/discovery/openapi.json"));
            using var contract = JsonDocument.Parse(normative);
            var schemas = contract.RootElement.GetProperty("components").GetProperty("schemas");
            using var response = await client.GetAsync("/api/v1/discovery");
            using var body = JsonDocument.Parse(await response.Content.ReadAsByteArrayAsync());
            Validate(body.RootElement, schemas.GetProperty("Discovery"), schemas);
            using var invalid = await client.GetAsync("/api/v1/discovery?invented-private-query=invented-private-value");
            Assert.Equal(HttpStatusCode.BadRequest, invalid.StatusCode);
            var problemText = await invalid.Content.ReadAsStringAsync();
            Assert.DoesNotContain("invented-private", problemText);
            using var problem = JsonDocument.Parse(problemText);
            Validate(problem.RootElement, schemas.GetProperty("Problem"), schemas);
            foreach (var path in new[] { "/api/v1/discovery", "/api/v1/discovery/openapi.json" })
            {
                using var head = await client.SendAsync(new(HttpMethod.Head, path));
                Assert.Equal(HttpStatusCode.MethodNotAllowed, head.StatusCode);
                Assert.Contains("no-store", head.Headers.CacheControl!.ToString());
                using var conditional = new HttpRequestMessage(HttpMethod.Get, path);
                conditional.Headers.TryAddWithoutValidation("If-None-Match", "*");
                using var fresh = await client.SendAsync(conditional);
                Assert.Equal(HttpStatusCode.OK, fresh.StatusCode);
                Assert.Null(fresh.Headers.ETag);
                Assert.False(fresh.Headers.Contains("Access-Control-Allow-Credentials"));
            }
        }
    }

    internal static void Validate(JsonElement value, JsonElement schema, JsonElement schemas)
    {
        if (schema.TryGetProperty("$ref", out var reference))
        { Validate(value, schemas.GetProperty(reference.GetString()!.Split('/')[^1]), schemas); return; }
        if (schema.TryGetProperty("const", out var constant)) { Assert.Equal(constant.GetRawText(), value.GetRawText()); }
        if (schema.TryGetProperty("enum", out var states))
        { Assert.Contains(states.EnumerateArray(), state => state.GetRawText() == value.GetRawText()); }
        if (value.ValueKind == JsonValueKind.Null)
        {
            Assert.Contains(schema.GetProperty("type").EnumerateArray(), type => type.GetString() == "null");
            return;
        }
        if (schema.TryGetProperty("type", out var type))
        {
            var types = type.ValueKind == JsonValueKind.Array
                ? type.EnumerateArray().Select(item => item.GetString()).ToArray() : [type.GetString()];
            var actual = value.ValueKind switch
            {
                JsonValueKind.Object => "object",
                JsonValueKind.Array => "array",
                JsonValueKind.String => "string",
                JsonValueKind.True or JsonValueKind.False => "boolean",
                JsonValueKind.Number when value.TryGetInt64(out _) => "integer",
                JsonValueKind.Number => "number",
                _ => "invalid"
            };
            Assert.Contains(actual, types);
        }
        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                if (schema.TryGetProperty("required", out var required))
                { foreach (var name in required.EnumerateArray()) { Assert.True(value.TryGetProperty(name.GetString()!, out _), name.GetString()); } }
                var properties = schema.GetProperty("properties");
                foreach (var property in value.EnumerateObject())
                {
                    Assert.True(properties.TryGetProperty(property.Name, out var definition), property.Name);
                    Validate(property.Value, definition, schemas);
                }
                if (value.TryGetProperty("secret", out var secret) && secret.GetBoolean())
                {
                    Assert.Equal("secret", value.GetProperty("type").GetString());
                    Assert.False(value.TryGetProperty("allowedValues", out _));
                    Assert.False(value.TryGetProperty("publicDefault", out _));
                }
                break;
            case JsonValueKind.Array:
                if (schema.TryGetProperty("maxItems", out var maximum)) { Assert.InRange(value.GetArrayLength(), 0, maximum.GetInt32()); }
                if (schema.TryGetProperty("minItems", out var minimum)) { Assert.True(value.GetArrayLength() >= minimum.GetInt32()); }
                if (schema.TryGetProperty("uniqueItems", out var unique) && unique.GetBoolean())
                { Assert.Equal(value.GetArrayLength(), value.EnumerateArray().Select(item => item.GetRawText()).Distinct().Count()); }
                foreach (var item in value.EnumerateArray()) { Validate(item, schema.GetProperty("items"), schemas); }
                break;
            case JsonValueKind.String:
                var text = value.GetString()!;
                if (schema.TryGetProperty("maxLength", out var length)) { Assert.InRange(text.Length, 0, length.GetInt32()); }
                if (schema.TryGetProperty("pattern", out var pattern)) { Assert.Matches(pattern.GetString()!, text); }
                if (schema.TryGetProperty("format", out var format))
                {
                    if (format.GetString() == "uuid") { Assert.True(Guid.TryParse(text, out _)); }
                    if (format.GetString() == "date-time") { Assert.True(DateTimeOffset.TryParse(text, out _)); }
                }
                break;
        }
    }
}
