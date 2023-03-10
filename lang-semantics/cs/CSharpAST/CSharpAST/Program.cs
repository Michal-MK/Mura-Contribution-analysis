using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using System.Text.Json.Nodes;

if (args.Length == 0) {
	return 1;
}

string configurationPath = args[0];
string filePath = args[1];

Dictionary<string, SyntaxKind> SUPPORTED_DECLARATIONS = new() {
	{ "class", SyntaxKind.ClassDeclaration },
	{ "function", SyntaxKind.MethodDeclaration },
	{ "property", SyntaxKind.PropertyDeclaration },
	{ "field", SyntaxKind.FieldDeclaration },
	{ "namespace", SyntaxKind.NamespaceDeclaration }
};

Dictionary<SyntaxKind, string> REVERSE_SUPPORTED_DECLARATIONS = SUPPORTED_DECLARATIONS.ToDictionary(input => input.Value, input => input.Key);

string[] expectedDeclarations = ((JsonArray)JsonNode.Parse(File.ReadAllText(configurationPath))).Select(s => s.GetValue<string>()).ToArray();

bool IsSupportedNodeOrToken(SyntaxNodeOrToken nodeOrToken) {
	return SUPPORTED_DECLARATIONS.Values.Contains(nodeOrToken.Kind());
}

string fileContent = File.ReadAllText(filePath);
var ast = SyntaxFactory.ParseSyntaxTree(fileContent);
var compilationUnit = ast.GetCompilationUnitRoot();

var nodesAndTokens = compilationUnit.DescendantNodesAndTokensAndSelf();

foreach (var descendant in nodesAndTokens.Where(IsSupportedNodeOrToken)) {
	string kind = REVERSE_SUPPORTED_DECLARATIONS[descendant.Kind()];
	if (!expectedDeclarations.Contains(kind)) {
		continue;
	}
	Console.WriteLine($"{kind} - [{descendant.Span.Start}-{descendant.Span.End}]");
}

return 0;