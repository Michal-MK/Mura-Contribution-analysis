using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using System.Text.Json.Nodes;
using Microsoft.CodeAnalysis.CSharp.Syntax;

if (args.Length == 0) {
	return 1;
}

string configurationPath = args[0];
string[] filePaths = args[1..];

Dictionary<string, SyntaxKind> SUPPORTED_DECLARATIONS = new() {
	{ "class", SyntaxKind.ClassDeclaration },
	{ "function", SyntaxKind.MethodDeclaration },
	{ "property", SyntaxKind.PropertyDeclaration },
	{ "field", SyntaxKind.FieldDeclaration },
	{ "namespace", SyntaxKind.NamespaceDeclaration },
};

Dictionary<SyntaxKind, string> REVERSE_SUPPORTED_DECLARATIONS = SUPPORTED_DECLARATIONS.ToDictionary(input => input.Value, input => input.Key);

string[] expectedDeclarations = ((JsonArray)JsonNode.Parse(File.ReadAllText(configurationPath))).Select(s => s.GetValue<string>()).ToArray();

bool IsSupportedNodeOrToken(SyntaxNodeOrToken nodeOrToken) {
	return SUPPORTED_DECLARATIONS.Values.Contains(nodeOrToken.Kind())
		|| nodeOrToken.Kind() == SyntaxKind.MultiLineCommentTrivia
		|| nodeOrToken.Kind() == SyntaxKind.SingleLineCommentTrivia;
}

string ReverseKind(SyntaxKind kind) {
	if (kind is SyntaxKind.MultiLineCommentTrivia or SyntaxKind.SingleLineCommentTrivia) {
		return "comment";
	}
	return REVERSE_SUPPORTED_DECLARATIONS[kind];
}

foreach (string filePath in filePaths) {
	Console.WriteLine(filePath);

	string fileContent = File.ReadAllText(filePath);
	SyntaxTree ast = SyntaxFactory.ParseSyntaxTree(fileContent);
	CompilationUnitSyntax compilationUnit = ast.GetCompilationUnitRoot();

	IEnumerable<SyntaxNodeOrToken> nodesAndTokens = compilationUnit.DescendantNodesAndTokensAndSelf();

	foreach (var descendant in nodesAndTokens.Where(IsSupportedNodeOrToken)) {
		string kind = ReverseKind(descendant.Kind());
		if (!expectedDeclarations.Contains(kind)) {
			continue;
		}
		Console.WriteLine($"{kind} - [{descendant.Span.Start}-{descendant.Span.End}]");
	}

	foreach (SyntaxTrivia trivia in compilationUnit.DescendantTrivia()
				 .Where(w => w.IsKind(SyntaxKind.SingleLineCommentTrivia)
							 || w.IsKind(SyntaxKind.MultiLineCommentTrivia)
							 || w.IsKind(SyntaxKind.SingleLineDocumentationCommentTrivia)
							 || w.IsKind(SyntaxKind.MultiLineDocumentationCommentTrivia))) {
		Console.WriteLine($"comment - [{trivia.Span.Start}-{trivia.Span.End}]");
	}
}

return 0;