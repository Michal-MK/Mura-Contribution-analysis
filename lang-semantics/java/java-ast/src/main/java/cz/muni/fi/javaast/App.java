package cz.muni.fi.javaast;

import com.puppycrawl.tools.checkstyle.JavaParser;
import com.puppycrawl.tools.checkstyle.api.CheckstyleException;
import com.puppycrawl.tools.checkstyle.api.DetailAST;
import com.puppycrawl.tools.checkstyle.api.TokenTypes;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;

import org.json.JSONArray;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.stream.Collectors;

public class App {
    public static void main(String[] args) {
        try {
            if (args.length < 2) {
                System.out.println("Usage: java -jar javaast.jar <path_to_declarations.json> <path_to_file.java>...");
                return;
            }
            new App().parse(args[0], Arrays.stream(args).skip(1).toArray(String[]::new));
        } catch (CheckstyleException | IOException e) {
            System.out.println("Error: " + e.getMessage());
        }
    }

    private void parse(String declarationsFile, String[] javaFiles) throws CheckstyleException, IOException {
        for (String javaFile : javaFiles) {
            System.out.println(javaFile);
            DetailAST result = JavaParser.parseFile(new File(javaFile), JavaParser.Options.WITH_COMMENTS);

            String content = Files.readString(Paths.get(declarationsFile));
            JSONArray declarations = new JSONArray(content);

            analyze(declarations.toList().stream().map(Object::toString).collect(Collectors.toList()), result);
        }
    }

    private static final HashMap<Integer, String> TYPE_MAP = new HashMap<>() {{
        put(TokenTypes.CLASS_DEF, "class");
        put(TokenTypes.METHOD_DEF, "function");
        put(TokenTypes.CTOR_DEF, "function");
        put(TokenTypes.VARIABLE_DEF, "field");
        put(TokenTypes.SINGLE_LINE_COMMENT, "comment");
        put(TokenTypes.BLOCK_COMMENT_BEGIN, "comment");
    }};

    private void analyze(List<String> declarations, DetailAST token) {
        if (token == null) {
            return;
        }

        var type = token.getType();

        if (TYPE_MAP.keySet().stream().anyMatch(t -> t == type) && declarations.contains(TYPE_MAP.get(type))) {
            if (type != TokenTypes.VARIABLE_DEF || !hasMethodParent(token)) {
                printToken(token);
            }
        }

        analyze(declarations, token.getFirstChild());
        analyze(declarations, token.getNextSibling());
    }

    private boolean hasMethodParent(DetailAST token) {
        DetailAST parent = token.getParent();
        while (parent != null) {
            if (parent.getType() == TokenTypes.METHOD_DEF) {
                return true;
            }
            parent = parent.getParent();
        }
        return false;
    }

    private void printToken(DetailAST token) {
        DetailAST lastChild = token;
        while (lastChild.getChildCount() > 0) {
            lastChild = lastChild.getLastChild();
        }
        int startLine = token.getLineNo();
        int endLine = lastChild.getLineNo();
        System.out.println(TYPE_MAP.get(token.getType()) + " - [" + startLine + "-" + endLine + "]");
    }
}
