from dataclasses import dataclass
from typing import Callable, List

from telegram import MessageEntity
from telegram.constants import MessageEntityType


MARKDOWN_SUPPORTED_LANGUAGES = {
    ".ignore",
    ".properties",
    "ABAP",
    "ABNF",
    "AL",
    "ANTLR4",
    "APL",
    "AQL",
    "ARFF",
    "AWK",
    "ActionScript",
    "Ada",
    "Agda",
    "Apex",
    "AppleScript",
    "Arduino",
    "Arturo",
    "AsciiDoc",
    "AutoHotkey",
    "AutoIt",
    "AviSynth",
    "BASIC",
    "BBcode",
    "BBj",
    "BNF",
    "BQN",
    "Bash",
    "Batch",
    "Bicep",
    "Birb",
    "Bison",
    "Brainfuck",
    "BrightScript",
    "Bro",
    "C",
    "C#",
    "C++",
    "C-like",
    "CFScript",
    "CIL",
    "CMake",
    "COBOL",
    "CSS",
    "CSV",
    "CUE",
    "ChaiScript",
    "Cilk/C",
    "Cilk/C++",
    "Clojure",
    "CoffeeScript",
    "Concurnas",
    "Content-Security-Policy",
    "Cooklang",
    "Crystal",
    "Cypher",
    "D",
    "DAX",
    "Dart",
    "DataWeave",
    "Dhall",
    "Diff",
    "Django/Jinja2",
    "Docker",
    "EBNF",
    "EJS",
    "ERB",
    "EditorConfig",
    "Eiffel",
    "Elixir",
    "Elm",
    "Erlang",
    "F#",
    "Factor",
    "False",
    "Fift",
    "Flow",
    "Fortran",
    "FunC",
    "G-code",
    "GDScript",
    "GEDCOM",
    "GLSL",
    "GN",
    "Git",
    "Go",
    "Gradle",
    "GraphQL",
    "Groovy",
    "HCL",
    "HLSL",
    "HTTP",
    "Haml",
    "Handlebars",
    "Haskell",
    "Haxe",
    "Hoon",
    "IchigoJam",
    "Icon",
    "Idris",
    "Ini",
    "Io",
    "J",
    "JQ",
    "JSDoc",
    "JSON",
    "JSON5",
    "JSONP",
    "Java",
    "JavaDoc",
    "JavaDoc-like",
    "JavaScript",
    "Jolie",
    "Julia",
    "Keyman",
    "Kotlin",
    "Kusto",
    "LOLCODE",
    "LaTeX",
    "Latte",
    "Less",
    "LilyPond",
    "Liquid",
    "Lisp",
    "LiveScript",
    "Lua",
    "MATLAB",
    "MAXScript",
    "MEL",
    "METAFONT",
    "Makefile",
    "Markdown",
    "Markup",
    "Mata",
    "Mermaid",
    "Mizar",
    "MongoDB",
    "Monkey",
    "MoonScript",
    "N1QL",
    "N4JS",
    "NASM",
    "NEON",
    "NSIS",
    "Nevod",
    "Nim",
    "Nix",
    "OCaml",
    "Objective-C",
    "Odin",
    "OpenCL",
    "OpenQasm",
    "Oz",
    "PARI/GP",
    "PC-Axis",
    "PHP",
    "PHPDoc",
    "PL/SQL",
    "Parser",
    "Pascal",
    "Pascaligo",
    "PeopleCode",
    "Perl",
    "PlantUML",
    "PowerQuery",
    "PowerShell",
    "Processing",
    "Prolog",
    "PromQL",
    "Pug",
    "Puppet",
    "PureBasic",
    "Python",
    "Q#",
    "QML",
    "Qore",
    "R",
    "Racket",
    "ReScript",
    "Reason",
    "Regex",
    "Rego",
    "Ren'py",
    "Rip",
    "Roboconf",
    "Ruby",
    "Rust",
    "SAS",
    "SML",
    "SQL",
    "Scala",
    "Scheme",
    "Smali",
    "Smalltalk",
    "Smarty",
    "Squirrel",
    "Stan",
    "Stylus",
    "SuperCollider",
    "Swift",
    "TAP",
    "TOML",
    "Tact",
    "Tcl",
    "Textile",
    "Tremor",
    "Twig",
    "TypeScript",
    "TypoScript",
    "URI",
    "UnrealScript",
    "V",
    "VB.Net",
    "VHDL",
    "Vala",
    "Velocity",
    "Verilog",
    "WGSL",
    "WarpScript",
    "WebAssembly",
    "Wren",
    "XQuery",
    "Xeora",
    "YAML",
    "YANG",
    "Zig",
    "abap",
    "abnf",
    "actionscript",
    "ada",
    "adoc",
    "agda",
    "al",
    "antlr4",
    "apacheconf",
    "apex",
    "apl",
    "applescript",
    "aql",
    "arduino",
    "arff",
    "arm-asm",
    "armasm",
    "art",
    "arturo",
    "asciidoc",
    "asm6502",
    "asmatmel",
    "aspnet",
    "atom",
    "autohotkey",
    "autoit",
    "avdl",
    "avisynth",
    "avro-idl",
    "avs",
    "awk",
    "bash",
    "basic",
    "batch",
    "bbcode",
    "bbj",
    "bicep",
    "birb",
    "bison",
    "bnf",
    "bqn",
    "brainfuck",
    "brightscript",
    "bro",
    "c",
    "cfc",
    "cfscript",
    "chaiscript",
    "cil",
    "cilk",
    "cilk-c",
    "cilk-cpp",
    "cilkc",
    "cilkcpp",
    "clike",
    "clojure",
    "cmake",
    "cobol",
    "coffee",
    "coffeescript",
    "conc",
    "concurnas",
    "context",
    "cooklang",
    "cpp",
    "crystal",
    "cs",
    "csharp",
    "cshtml",
    "csp",
    "css",
    "csv",
    "cue",
    "cypher",
    "d",
    "dart",
    "dataweave",
    "dax",
    "dhall",
    "diff",
    "django",
    "dns-zone",
    "dns-zone-file",
    "docker",
    "dockerfile",
    "dot",
    "dotnet",
    "ebnf",
    "editorconfig",
    "eiffel",
    "ejs",
    "elisp",
    "elixir",
    "elm",
    "emacs",
    "emacs-lisp",
    "erb",
    "erlang",
    "eta",
    "etlua",
    "excel-formula",
    "factor",
    "false",
    "fift",
    "firestore-security-rules",
    "flow",
    "fortran",
    "fsharp",
    "ftl",
    "func",
    "g4",
    "gamemakerlanguage",
    "gap",
    "gawk",
    "gcode",
    "gdscript",
    "gedcom",
    "gettext",
    "git",
    "gitignore",
    "glsl",
    "gml",
    "gn",
    "gni",
    "go",
    "go-mod",
    "go-module",
    "gradle",
    "grammars.dat",
    "graphql",
    "groovy",
    "gv",
    "haml",
    "handlebars",
    "haskell",
    "haxe",
    "hbs",
    "hcl",
    "hgignore",
    "hlsl",
    "hoon",
    "hpkp",
    "hs",
    "hsts",
    "html",
    "http",
    "ichigojam",
    "icon",
    "icu-message-format",
    "idr",
    "idris",
    "iecst",
    "ignore",
    "inform7",
    "ini",
    "ino",
    "io",
    "j",
    "java",
    "javadoc",
    "javadoclike",
    "javascript",
    "javastacktrace",
    "jinja2",
    "jolie",
    "jq",
    "js",
    "jsdoc",
    "json",
    "json5",
    "jsonp",
    "jsstacktrace",
    "jsx",
    "julia",
    "keepalived",
    "keyman",
    "kotlin",
    "kt",
    "kts",
    "kusto",
    "latex",
    "latte",
    "ld",
    "less",
    "libprisma/grammars.dat",
    "lilypond",
    "linker-script",
    "liquid",
    "lisp",
    "livescript",
    "llvm",
    "log",
    "lolcode",
    "lua",
    "ly",
    "magma",
    "makefile",
    "markdown",
    "markup",
    "markup-templating",
    "mata",
    "mathematica",
    "mathml",
    "matlab",
    "maxscript",
    "md",
    "mel",
    "mermaid",
    "metafont",
    "mizar",
    "mongodb",
    "monkey",
    "moon",
    "moonscript",
    "mscript",
    "mustache",
    "n1ql",
    "n4js",
    "n4jsd",
    "nand2tetris-hdl",
    "nani",
    "naniscript",
    "nasm",
    "nb",
    "neon",
    "nevod",
    "nginx",
    "nim",
    "nix",
    "npmignore",
    "nsis",
    "objc",
    "objectivec",
    "objectpascal",
    "ocaml",
    "odin",
    "opencl",
    "openqasm",
    "oz",
    "parigp",
    "parser",
    "pascal",
    "pascaligo",
    "pbfasm",
    "pcaxis",
    "pcode",
    "peoplecode",
    "perl",
    "php",
    "phpdoc",
    "plaintext",
    "plant-uml",
    "plantuml",
    "plsql",
    "po",
    "powerquery",
    "powershell",
    "pq",
    "processing",
    "prolog",
    "promql",
    "properties",
    "protobuf",
    "psl",
    "pug",
    "puppet",
    "purebasic",
    "px",
    "py",
    "python",
    "q",
    "qasm",
    "qml",
    "qore",
    "qs",
    "qsharp",
    "r",
    "racket",
    "razor",
    "rb",
    "rbnf",
    "reason",
    "regex",
    "rego",
    "renpy",
    "res",
    "rescript",
    "rest",
    "rip",
    "rkt",
    "roboconf",
    "robot",
    "robotframework",
    "rpy",
    "rss",
    "ruby",
    "rust",
    "sas",
    "sass",
    "scala",
    "scheme",
    "sclang",
    "scss",
    "sh",
    "sh-session",
    "shell",
    "shell-session",
    "shellsession",
    "shortcode",
    "sln",
    "smali",
    "smalltalk",
    "smarty",
    "sml",
    "smlnj",
    "sol",
    "solidity",
    "solution-file",
    "soy",
    "splunk-spl",
    "sqf",
    "sql",
    "squirrel",
    "ssml",
    "stan",
    "stata",
    "stylus",
    "supercollider",
    "svg",
    "swift",
    "systemd",
    "t4",
    "t4-cs",
    "t4-templating",
    "t4-vb",
    "tact",
    "tap",
    "tcl",
    "tex",
    "textile",
    "tl",
    "tlb",
    "toml",
    "tremor",
    "trickle",
    "troy",
    "ts",
    "tsconfig",
    "tsx",
    "tt2",
    "twig",
    "typescript",
    "typoscript",
    "uc",
    "unrealscript",
    "uorazor",
    "uri",
    "url",
    "uscript",
    "v",
    "vala",
    "vb",
    "vba",
    "vbnet",
    "velocity",
    "verilog",
    "vhdl",
    "vim",
    "visual-basic",
    "warpscript",
    "wasm",
    "web-idl",
    "webidl",
    "webmanifest",
    "wgsl",
    "wiki",
    "wl",
    "wolfram",
    "wren",
    "xeora",
    "xeoracube",
    "xls",
    "xlsx",
    "xml",
    "xojo",
    "xquery",
    "yaml",
    "yang",
    "yml",
    "zig",
}

MARKDOWN_SUPPORTED_LANGUAGES = set(map(lambda x: x.lower(), MARKDOWN_SUPPORTED_LANGUAGES))

TEXT_LENGTH_LIMIT = 4096


def find_special_sequences(text: str):
    """
    find all special sequences (continuous special characters, length >= 8)
    """
    results: list[tuple[int, int]] = []
    COUNT_LIMIT = 8
    # 定义一个函数来判断字符是否为特殊字符或空格

    def is_special_char(char):
        return not ((ord('A') <= ord(char) <= ord('Z')) or (ord('a') <= ord(char) <= ord('z')) or (ord('0') <= ord(char) <= ord('9')) or '\u4e00' <= char <= '\u9fa5')

    def is_true_special_char(char):
        if char in ("`", "*", "_", "~", ";", ":", "(", ")", "[", "]", "{", "}", "<", ">", "#", "+", "-", "=", "|", ".", "!", "$", "%", ' ', '\n', '，', '！', '：'):
            return False
        return is_special_char(char)
    for index, char in enumerate(text):
        if len(results) > 0 and results[-1][0] <= index < results[-1][1]:
            continue
        # 判断当前字符是否为特殊符号或空格
        if not is_true_special_char(char):
            continue
        last_end = results[-1][1] if len(results) > 0 else -1
        # scan nearby special char and count them
        start = index
        for i in range(index - 1, last_end, -1):
            if not is_special_char(text[i]):
                break
            start = i
        end = index + 1
        for i in range(index + 1, len(text)):
            if not is_special_char(text[i]):
                break
            end = i + 1
        if end - start >= COUNT_LIMIT:
            space_test_fail = False
            last_is_space = False
            for i in range(start, end):
                if last_is_space:
                    if text[i].isspace():
                        space_test_fail = True
                        break
                    else:
                        last_is_space = False
                else:
                    if text[i].isspace():
                        last_is_space = True
            if not space_test_fail:
                results.append((start, end))
    return results


def force_longtext_split(txt: List[str]) -> List[str]:
    counting = 0
    i = 0
    ans: List[str] = []
    sep_len = 0
    while i < len(txt):
        if counting + len(txt[i]) < TEXT_LENGTH_LIMIT - sep_len:
            counting += len(txt[i])
            sep_len = 1
            i += 1
        else:
            if i == 0:
                # too long, must split
                super_long_line = txt[0]
                _end = min(1000, len(super_long_line))
                part = super_long_line[:_end]
                txt[0] = super_long_line[_end:]
                ans.append(part)
                continue
            else:
                ans.append("\n".join(txt[:i]))
                txt = txt[i:]
                i = 0
                sep_len = 0
                counting = 0
    if len(txt) > 0:
        ans.append("\n".join(txt))
    return ans


def longtext_split(txt: str) -> List[str]:
    if len(txt) < TEXT_LENGTH_LIMIT:
        return [txt]
    txts = txt.split("\n")
    ans: List[str] = []
    # search for ``` of markdown block
    dotsss_start = -1
    dotsss_end = -1
    for i in range(len(txts)):
        if txts[i].startswith("```"):
            if dotsss_start == -1:
                dotsss_start = i
            else:
                dotsss_end = i
                break
    if dotsss_start != -1 and dotsss_end != -1:
        if dotsss_start == 0 and dotsss_end == len(txts) - 1:
            # cannot keep markdown block!!!
            return force_longtext_split(txts)
        parts = txts[:dotsss_start], txts[dotsss_start:dotsss_end + 1], txts[dotsss_end + 1:]
        for i, part in enumerate(parts):
            if len(part) > 0:
                if i == 0:
                    ans.extend(force_longtext_split(part))
                else:
                    this_text = "\n".join(part)
                    ans.extend(longtext_split(this_text))
        return ans
    #
    return force_longtext_split(txts)


@dataclass
class TextObject:
    text: str
    entity_type: MessageEntityType | None
    code_language: str | None = None


def trim_spaces_before_line(code: str):
    lines = code.split("\n")
    if len(lines) == 0:
        return code
    COMMON_SPACE_MAX = 5000
    common_spaces = COMMON_SPACE_MAX
    for line in lines:
        if not line.strip():
            continue
        spaces_count = len(line) - len(line.lstrip(' '))
        common_spaces = min(common_spaces, spaces_count)
        if common_spaces == 0:
            return code
    if COMMON_SPACE_MAX == common_spaces:
        return code

    def xstrip(line: str):
        if not line.strip():
            return ""
        return line[common_spaces:]
    code = "\n".join(xstrip(line) for line in lines)
    return code


class MarkdownParser:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.entities: list[list[MessageEntity]] = []
        self.cur_text_couting = 0
        self.rest_text_object: list[TextObject] = []

    def enqueue(self, text_object: TextObject):
        if len(text_object.text) > 0:
            self.rest_text_object.append(text_object)
            self.cur_text_couting += len(text_object.text)

    @classmethod
    def recursive_markdown_escape_except_block(cls, s: str, partition_func: Callable[[str], list[TextObject]], recursive_escape_func: Callable[[str], list[TextObject]]) -> list[TextObject]:
        partitioned = partition_func(s)
        ret = []
        if len(partitioned) % 2 == 1:
            for i, value in enumerate(partitioned):
                if i % 2 == 0:
                    ret += recursive_escape_func(value.text)
                else:
                    ret.append(value)
        return ret

    @classmethod
    def split_special(cls, text: str) -> list[str]:
        special_sequences = find_special_sequences(text)
        ret = []
        cur = 0
        for start, end in special_sequences:
            ret.append(text[cur:start])
            ret.append(text[start:end])
            cur = end
        ret.append(text[cur:])
        return ret

    def feed(self, text: str, is_codeblock: bool):
        text = text.strip()
        if is_codeblock:
            code, code_lang = self.get_code_lang(text)
            code = trim_spaces_before_line(code)
            self.enqueue(TextObject(text=code, entity_type=MessageEntityType.PRE, code_language=code_lang))
        else:
            lines = text.split("\n")
            sep = ""
            for line in lines:
                self.push_text(sep + line, [(self.split_special, None), ("`", MessageEntityType.CODE),
                               ("**", MessageEntityType.BOLD), ("*", MessageEntityType.ITALIC)])
                sep = "\n"
        self.digest()

    @classmethod
    def get_code_lang(cls, text: str):
        _left, _sep, _right = text.partition("\n")
        code_lang = None
        if _sep == "\n" and _left.lower() in MARKDOWN_SUPPORTED_LANGUAGES:
            code_lang = _left
            code = _right
        else:
            code = text
        return code, code_lang

    @classmethod
    def join_escaped(cls, splitted: list[str]) -> list[str]:
        ret = []
        left_over = ""
        for split_text in splitted:
            if split_text.endswith('\\'):
                # count last continuous backslash
                count = 0
                for i in range(len(split_text) - 1, -1, -1):
                    if split_text[i] == '\\':
                        count += 1
                    else:
                        break
                if count % 2 == 1:
                    left_over += split_text
                    continue
            ret.append(left_over + split_text)
            left_over = ""
        if left_over:
            ret.append(left_over)
        return ret

    def push_text(self, text: str, split_config: list[tuple[str | Callable[[str], list[str]], MessageEntityType | None]]):
        splitter = split_config[0][0]
        if isinstance(splitter, str):
            splitted = text.split(splitter)
            if len(splitter) == 1:
                splitted = self.join_escaped(splitted)
        else:
            splitted = splitter(text)
        if len(splitted) % 2 == 1:
            for i, sub_text in enumerate(splitted):
                if i % 2 == 0:
                    if len(split_config) == 1:
                        self.enqueue(TextObject(text=text, entity_type=None))
                    else:
                        self.push_text(sub_text, split_config[1:])
                else:
                    self.enqueue(TextObject(text=sub_text, entity_type=split_config[0][1]))
            return
        self.enqueue(TextObject(text=text, entity_type=None))

    @classmethod
    def _digest(cls, rest_text_object: list[TextObject]) -> tuple[str, list[MessageEntity], list[TextObject]]:
        text = ""
        entities = []
        end_at = len(rest_text_object)
        for i, text_object in enumerate(rest_text_object):
            if len(text + text_object.text) >= TEXT_LENGTH_LIMIT:
                end_at = i
                break
            if text_object.entity_type is not None:
                new_entity = MessageEntity(text_object.entity_type, offset=len(text), length=len(text_object.text), language=text_object.code_language)
                entities.append(new_entity)
            text += text_object.text
        return text, entities, rest_text_object[end_at:]

    def digest(self):
        if self.cur_text_couting < TEXT_LENGTH_LIMIT:
            return
        assert len(self.rest_text_object) > 0
        for text_object in self.rest_text_object:
            if len(text_object.text) >= TEXT_LENGTH_LIMIT:
                # too long, will force split
                self.force_split_up()
                break
        while self.cur_text_couting >= TEXT_LENGTH_LIMIT:
            text, entities, self.rest_text_object = self._digest(self.rest_text_object)
            self._update_text_counting()
            if text:
                self.texts.append(text)
                self.entities.append(entities)

    def force_split_up(self):
        text_objects = self.rest_text_object
        self.rest_text_object = sum((self.force_split_up_text_object(x) for x in text_objects), [])
        self.rest_text_object = list(filter(lambda x: len(x.text) > 0, self.rest_text_object))
        self._update_text_counting()

    def _update_text_counting(self):
        self.cur_text_couting = sum(len(x.text) for x in self.rest_text_object)

    def digest_final(self):
        text, entities, self.rest_text_object = self._digest(self.rest_text_object)
        assert 0 == len(self.rest_text_object)
        if text:
            self.texts.append(text)
            self.entities.append(entities)
        self.fix_entities_offset()
        return self.texts, self.entities

    def fix_entities_offset(self):
        for text, entities in zip(self.texts, self.entities):
            cur_index = 0
            accumulated_len = 0
            for i, entity in enumerate(entities):
                cur_text = text[cur_index:entity.offset]
                accumulated_len += len(cur_text.encode('utf-16-le'))
                cur_off = accumulated_len // 2
                cur_text = text[entity.offset:entity.offset + entity.length]
                accumulated_len += len(cur_text.encode('utf-16-le'))
                cur_len = accumulated_len // 2 - cur_off
                entities[i] = MessageEntity(offset=cur_off, length=cur_len, type=entity.type, language=entity.language)
                cur_index = entity.offset + entity.length

    @classmethod
    def force_split_up_text_object(cls, text_object: TextObject) -> list[TextObject]:
        if len(text_object.text) < TEXT_LENGTH_LIMIT:
            return [text_object]
        parted_1, parted_2 = cls.split_2_parts(text_object.text)
        kwargs: dict = {"entity_type": text_object.entity_type}
        if text_object.entity_type == MessageEntityType.PRE:
            kwargs["code_language"] = text_object.code_language
        return [TextObject(text=parted_1, **kwargs)] + cls.force_split_up_text_object(TextObject(text=parted_2, **kwargs))

    @classmethod
    def split_2_parts(self, long_text: str) -> tuple[str, str]:
        long_text = long_text.strip()
        first_part = long_text[:TEXT_LENGTH_LIMIT]
        last_part = long_text[TEXT_LENGTH_LIMIT:]
        split_first_part = first_part.rpartition("\n")
        if split_first_part[1] == "\n" and split_first_part[0]:
            parted_1 = split_first_part[0]
            parted_2 = split_first_part[2] + last_part
        else:
            parted_1 = first_part
            parted_2 = last_part
        return parted_1, parted_2

    def parse(self, txt: str) -> tuple[list[str], list[list[MessageEntity]]]:
        first_level_split = txt.split("```")
        if len(first_level_split) % 2 == 0:
            # broken code block, or no code block
            first_level_split = [txt]

        for i, txt_part in enumerate(first_level_split):
            self.feed(txt_part, is_codeblock=i % 2 == 1)
        return self.digest_final()


def longtext_markdown_split(txt: str) -> tuple[list[str], list[list[MessageEntity]]]:
    splitter = MarkdownParser()
    return splitter.parse(txt)
