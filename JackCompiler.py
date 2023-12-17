import re
import sys
import os

#sys.argv.append('D:/Year2/Systems/nand2tetris/projects/11/Average')


class SymbolTable:

    def __init__(self):
        self.static_counter = 0
        self.field_counter = 0
        self.arg_counter = 0
        self.var_counter = 0
        self.vars = []

    def reset(self):
        self.static_counter = 0
        self.field_counter = 0
        self.arg_counter = 0
        self.var_counter = 0
        self.vars = []

    def define(self, name, typ, kind):
        if kind == "STATIC":
            self.vars.append((name, typ, "STATIC", self.static_counter))
            self.static_counter += 1
        elif kind == "FIELD":
            self.vars.append((name, typ, "FIELD", self.field_counter))
            self.field_counter += 1
        elif kind == "ARG":
            self.vars.append((name, typ, "ARG", self.arg_counter))
            self.arg_counter += 1
        elif kind == "VAR":
            self.vars.append((name, typ, "VAR", self.var_counter))
            self.var_counter += 1

    def var_count(self, kind):
        if kind == "STATIC":
            return self.static_counter
        elif kind == "FIELD":
            return self.field_counter
        elif kind == "ARG":
            return self.arg_counter
        elif kind == "VAR":
            return self.var_counter


    def kind_of(self, name):
        for tup in self.vars:
            if tup[0] == name:
                return tup[2]
        return None

    def type_of(self, name):
        for tup in self.vars:
            if tup[0] == name:
                return tup[1]
        return None

    def index_of(self, name):
        for tup in self.vars:
            if tup[0] == name:
                return tup[3]
        return None

    def __str__(self):
        return str(self.vars)


class VMWriter:
    def __init__(self, file):
        self.out = open(file.replace('.jack', '.vm'), 'w+')

    def write_push(self, segment, index):
        if segment == 'ARG':
            segment = 'argument'
        self.out.write(f"push {segment.lower()} {index}\n")

    def write_pop(self, segment, index):
        if segment == 'ARG':
            segment = 'argument'
        self.out.write(f"pop {segment.lower()} {index}\n")

    def write_arithmetic(self, command):
        self.out.write(f"{command.lower()}\n")

    def write_label(self, label):
        self.out.write(f"label {label}\n")

    def write_goto(self, label):
        self.out.write(f"goto {label}\n")

    def write_if(self, label):
        self.out.write(f"if-goto {label}\n")

    def write_call(self, name, nvars):
        self.out.write(f"call {name} {nvars}\n")

    def write_function(self, name, nvars):
        self.out.write(f"function {name} {nvars}\n")

    def write_return(self):
        self.out.write("return\n")

    def close(self):
        self.out.close()


class Tokenizer:
    keyword_keys = ['class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int', 'char', 'boolean',
                    'void',
                    'true', 'false', 'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return']
    symbol_keys = ['{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/', '&', '|', '<', '>', '=', '~']

    def __init__(self, source):
        self.file = open(source)
        self.file.read()
        self.num_chars = self.file.tell()
        self.file.seek(0)
        self.token = None
        self.endOfFile = False

    def has_more_tokens(self):
        position = self.file.tell()
        if position == self.num_chars:
            return False
        return True

    def advance(self):
        word = ''
        adv = True
        while adv:
            position = self.file.tell()
            char = self.file.read(1)
            if char == '/':
                char = self.file.read(1)
                if char == '/':
                    self.file.readline()
                elif char == '*':
                    self.file.read(1)
                    while self.file.read(2) != '*/':
                        adv = True
                        self.file.seek(self.file.tell() - 1)
                    self.file.read(1)
                else:
                    self.file.seek(position)
                    char = self.file.read(1)
                    word += char

            elif re.match(r"^\s+", char):
                if word != '':
                    self.token = word
                    adv = False
            elif char in self.symbol_keys:
                adv = False
                if word != '':
                    self.token = word
                    self.file.seek(position)
                else:
                    self.token = char
            elif char == '"':
                word = char
                char = self.file.read(1)
                while char != '"':
                    word += char
                    char = self.file.read(1)
                word += char
                self.token = word
            else:
                word += char
            if not self.has_more_tokens():
                adv = False

    def token_type(self):
        if self.token in self.symbol_keys:
            if self.token == "<":
                self.token = "&lt;"
            elif self.token == ">":
                self.token = "&gt;"
            elif self.token == '"':
                self.token = "&quot;"
            elif self.token == "&":
                self.token = "&amp;"
            return "symbol"
        elif self.token in self.keyword_keys:
            return "keyword"
        elif self.token.isdecimal():
            return "integerConstant"
        elif self.token.startswith('"') and self.token.endswith('"'):
            self.token = self.token[1:-1]
            return "stringConstant"
        else:
            return "identifier"


class VM_agent:
    CONVERT_KIND = {
        'ARG': 'ARG',
        'STATIC': 'STATIC',
        'VAR': 'LOCAL',
        'FIELD': 'THIS'
    }

    ARITHMETIC = {
        '+': 'ADD',
        '-': 'SUB',
        '=': 'EQ',
        '&gt;': 'GT',
        '&lt;': 'LT',
        '&amp;': 'AND',
        '|': 'OR'
    }

    ARITHMETIC_UNARY = {
        '-': 'NEG',
        '~': 'NOT'
    }

    def __init__(self, token_file, vm_writer):
        self.class_name = ''
        self.vm_writer = vm_writer
        self.token_file = token_file
        self.current_token = ''
        self.while_index = -1
        self.if_index = -1
        self.class_symbol_table = SymbolTable()
        self.subroutine_symbol_table = SymbolTable()
        self.is_function = False

    def ignore(self):
        self.token_file.readline()

    def get_token(self):
        self.current_token = self.token_file.readline()
        self.current_token = self.current_token.split()[1]
        return self.current_token

    def get_string_token(self):
        position = self.token_file.tell()
        string_to_return = self.token_file.readline()
        self.token_file.seek(position)
        start = len("<stringConstant> ")
        end = string_to_return.find(" </stringConstant>")
        string_to_return = string_to_return[start:end]
        return string_to_return

    def peek_next_token(self):
        position = self.token_file.tell()
        token_to_return = self.token_file.readline()
        if 'tokens' in token_to_return or token_to_return == '':
            return 'Done'
        token_to_return = token_to_return.split()[1]
        self.token_file.seek(position)
        return token_to_return

    def peek_next_token_type(self):
        position = self.token_file.tell()
        type_to_return = self.token_file.readline()
        type_to_return = type_to_return.split()[0]
        self.token_file.seek(position)
        return type_to_return

    def get_var_type(self, var_name):
        if self.class_symbol_table.kind_of(var_name) is not None:
            return self.class_symbol_table.type_of(var_name)
        else:
            return self.subroutine_symbol_table.type_of(var_name)

    def get_var_kind(self, var_name):
        if self.class_symbol_table.kind_of(var_name) is not None:
            return self.class_symbol_table.kind_of(var_name)
        else:
            return self.subroutine_symbol_table.kind_of(var_name)

    def get_var_index(self, var_name):
        if self.class_symbol_table.kind_of(var_name) is not None:
            return self.class_symbol_table.index_of(var_name)
        else:
            return self.subroutine_symbol_table.index_of(var_name)

    def insert_to_table(self, name, typ, kind):
        if kind == 'field' or kind == 'static':
            self.class_symbol_table.define(name, typ, kind.upper())
        else:
            self.subroutine_symbol_table.define(name, typ, kind.upper())

    def class_has_var_dec(self):
        return 'static' in self.peek_next_token() or 'field' in self.peek_next_token()

    def class_is_subroutine_dec(self):
        return 'constructor' in self.peek_next_token() or 'method' in self.peek_next_token() or 'function' in self.peek_next_token()

    def is_statement(self):
        return 'let' in self.peek_next_token() or 'if' in self.peek_next_token() or 'while' in self.peek_next_token() \
            or 'do' in self.peek_next_token() or 'return' in self.peek_next_token()

    def is_function_call(self):
        position = self.token_file.tell()
        self.get_token()
        next_token = self.get_token()
        self.token_file.seek(position)
        return next_token == '.'


    def is_array(self):
        position = self.token_file.tell()
        self.get_token()
        next_token = self.get_token()
        self.token_file.seek(position)
        return next_token == '['

    def is_keyword(self):
        position = self.token_file.tell()
        keyword = self.token_file.readline().split()[0]
        self.token_file.seek(position)
        return 'keyword' in keyword

    def is_unary_operation(self):
        return '-' in self.peek_next_token() or '~' in self.peek_next_token()

    def is_operation(self):
        return re.search(r'(\+|-|\*|/|&amp;|\||&lt;|&gt;|=|>|<|&)', self.peek_next_token())


    def compile_param_list(self):
        if ')' not in self.peek_next_token():
            typ = self.get_token()  # type
            name = self.get_token()  # varName
            self.subroutine_symbol_table.define(name, typ, 'ARG')

        while ')' not in self.peek_next_token():
            self.get_token()  # ,
            typ = self.get_token()  # type
            name = self.get_token()  # varName
            self.subroutine_symbol_table.define(name, typ, 'ARG')



    def compile_var_dec(self):
        num_args = 1
        kind = self.get_token()
        typ = self.get_token()
        name = self.get_token()
        self.insert_to_table(name, typ, kind)
        while self.get_token() == ',':
            self.insert_to_table(self.get_token(), typ, kind)
            num_args += 1
        return num_args


    def compile_term(self):
        if self.is_unary_operation():
            unary_operation = self.ARITHMETIC_UNARY[self.get_token()]
            self.compile_term()
            self.vm_writer.write_arithmetic(unary_operation)
        elif '(' in self.peek_next_token():
            self.get_token()
            self.compile_expression()
            self.get_token()
        else:
            if self.peek_next_token().isnumeric():
                self.vm_writer.write_push('constant', self.get_token())
            elif 'string' in self.peek_next_token_type():
                word = self.get_string_token()
                self.get_token()
                self.vm_writer.write_push('CONSTANT', len(word) + 1)
                self.vm_writer.write_call('String.new', 1)
                for char in word:
                    self.vm_writer.write_push('constant', ord(char))
                    self.vm_writer.write_call('String.appendChar', 2)
            elif self.is_array():
                arr_var = self.get_token()
                arr_kind = self.CONVERT_KIND[self.get_var_kind(arr_var)]
                arr_index = self.get_var_index(arr_var)
                self.vm_writer.write_push(arr_kind, arr_index)
                self.get_token()  # [
                self.compile_expression()
                self.get_token()  # ]
                self.vm_writer.write_arithmetic('ADD')
                self.vm_writer.write_pop('POINTER', 1)
                self.vm_writer.write_push('THAT', 0)
            elif self.is_keyword():
                keyword = self.get_token()
                if keyword == 'this':
                    self.vm_writer.write_push('POINTER', 0)
                else:
                    self.vm_writer.write_push('constant', 0)
                    if keyword == 'true':
                        self.vm_writer.write_arithmetic('NOT')

            elif self.is_function_call():
                self.compile_do(False)
            else:
                var_name = self.get_token()
                var_kind = self.CONVERT_KIND[self.get_var_kind(var_name)]
                var_index = self.get_var_index(var_name)
                self.vm_writer.write_push(var_kind, var_index)




    def compile_expression(self):
        self.compile_term()

        while self.is_operation():
            operation = self.get_token()
            self.compile_term()
            if operation in self.ARITHMETIC.keys():
                self.vm_writer.write_arithmetic(self.ARITHMETIC[operation])
            elif operation == '*':
                self.vm_writer.write_call('Math.multiply', 2)
            elif operation == '/':
                self.vm_writer.write_call('Math.divide', 2)


    def compile_expression_list(self):
        num_args = 0
        if ')' not in self.peek_next_token():
            num_args += 1
            self.compile_expression()

        while ')' not in self.peek_next_token():
            num_args += 1
            self.get_token()  # ,
            self.compile_expression()
        return num_args

    def compile_let(self):
        self.get_token()  # let
        var_name = self.get_token()  # var name
        var_kind = self.CONVERT_KIND[self.get_var_kind(var_name)]
        var_index = self.get_var_index(var_name)
        if var_kind is None and '.' not in self.peek_next_token():
            var_kind = self.class_symbol_table.kind_of(var_name)
        if '[' in self.peek_next_token():
            self.vm_writer.write_push(var_kind, var_index)
            self.get_token()  # [
            self.compile_expression()
            self.get_token()  # ]
            self.vm_writer.write_arithmetic('ADD')
            self.get_token()  # =
            self.compile_expression()
            self.vm_writer.write_pop('TEMP', 0)
            self.vm_writer.write_pop('POINTER', 1)
            self.vm_writer.write_push('TEMP', 0)
            self.vm_writer.write_pop('THAT', 0)
        else:
            self.get_token()  # =
            self.compile_expression()
            self.vm_writer.write_pop(var_kind, var_index)


    def compile_if(self):
        self.if_index += 1
        if_index = self.if_index
        self.get_token()  # if
        self.get_token()  # (
        self.compile_expression()  # if
        self.get_token()  # )
        self.get_token()  # {
        self.vm_writer.write_if('IF_TRUE' + str(if_index))
        self.vm_writer.write_goto('IF_FALSE' + str(if_index))
        self.vm_writer.write_label('IF_TRUE' + str(if_index))
        self.compile_statements()
        self.vm_writer.write_goto('IF_END' + str(if_index))
        self.get_token()
        self.vm_writer.write_label('IF_FALSE' + str(if_index))
        if 'else' in self.peek_next_token():
            self.get_token()  # else
            self.get_token()  # {
            self.compile_statements()
            self.get_token()  # }

        self.vm_writer.write_label('IF_END' + str(if_index))


    def compile_while(self):
        self.while_index += 1
        while_index = self.while_index
        self.vm_writer.write_label('START' + str(while_index))
        self.get_token()  # while
        self.compile_expression()
        self.vm_writer.write_arithmetic('NOT')
        self.vm_writer.write_if('END' + str(while_index))
        self.get_token()  # {
        self.compile_statements()
        self.vm_writer.write_goto('START' + str(while_index))
        self.vm_writer.write_label('END' + str(while_index))
        self.get_token()  # }

    def compile_do(self, direct):
        num_args = 0
        typ = False
        if direct:
            self.get_token()
        subroutine_name = self.get_token()
        if self.get_var_type(subroutine_name) is not None:
            var_kind = self.get_var_kind(subroutine_name)
            var_index = self.get_var_index(subroutine_name)
            subroutine_name = self.get_var_type(subroutine_name)
            typ = True
        if '.' in self.peek_next_token():
            if typ:
                self.vm_writer.write_push(self.CONVERT_KIND[var_kind], var_index)
                num_args += 1
                self.get_token()
                subroutine_name = subroutine_name + '.' + self.get_token()
            elif self.get_var_kind(subroutine_name) is None:
                self.get_token()
                subroutine_name = subroutine_name + '.' + self.get_token()
            else:
                self.vm_writer.write_push('THIS', 0)
                num_args += 1
                self.get_token()
                subroutine_name = subroutine_name + '.' + self.get_token()
        else:  # called from method in class
            num_args = 1
            self.vm_writer.write_push('POINTER', 0)
            subroutine_name = self.class_name + '.' + subroutine_name
        self.get_token()  # (
        num_args += self.compile_expression_list()
        self.vm_writer.write_call(subroutine_name, num_args)
        if direct:
            self.vm_writer.write_pop('TEMP', 0)
        self.get_token()  # )


    def compile_return(self):
        self.get_token()
        if ';' not in self.peek_next_token():
            self.compile_expression()
        else:
            self.vm_writer.write_push('CONSTANT', 0)
        self.get_token()
        self.vm_writer.write_return()

    def compile_statements(self):
        while self.is_statement():
            if 'let' in self.peek_next_token():
                self.compile_let()
                self.get_token()
            elif 'if' in self.peek_next_token():
                self.compile_if()
            elif 'while' in self.peek_next_token():
                self.compile_while()
            elif 'do' in self.peek_next_token():
                self.compile_do(True)
                self.get_token()
            elif 'return' in self.peek_next_token():
                self.compile_return()


    def compile_subroutine(self):
        num_args = 0
        self.is_function = False
        subroutine_kind = self.get_token()
        if subroutine_kind == 'function':
            self.is_function = True
        self.get_token()
        subroutine_name = self.class_name + '.' + self.get_token()

        if subroutine_kind == 'method':
            self.insert_to_table('instance', self.class_name, 'ARG')

        self.get_token()  # (
        self.compile_param_list()
        self.get_token()  # )
        self.get_token()  # {

        while 'var' in self.peek_next_token():
            num_args += self.compile_var_dec()

        self.vm_writer.write_function(subroutine_name, num_args)

        if subroutine_kind == 'constructor':
            num_fields = self.class_symbol_table.var_count('FIELD')
            self.vm_writer.write_push('constant', num_fields)
            self.vm_writer.write_call('Memory.alloc', 1)
            self.vm_writer.write_pop('POINTER', 0)
        elif subroutine_kind == 'method':
            self.vm_writer.write_push('ARG', 0)
            self.vm_writer.write_pop('POINTER', 0)
        self.compile_statements()
        self.get_token()  # }
        self.subroutine_symbol_table.reset()

    def compile_class(self):
        self.ignore()  # <tokens>
        self.get_token()  # class
        self.class_name = self.get_token()
        self.get_token()  # {

        while self.class_has_var_dec():
            self.compile_var_dec()

        while self.class_is_subroutine_dec():
            self.compile_subroutine()



def main():
    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        for file in os.listdir(sys.argv[1]):
            if file.endswith('.jack'):
                root = sys.argv[1] + '/' + file
                tokenizer = Tokenizer(root)
                out = open(root.replace('.jack', 'T.xml'), 'w+')
                out.write("<tokens>\n")
                while tokenizer.has_more_tokens():
                    tokenizer.advance()
                    type_of_token = tokenizer.token_type()
                    out.write(f"<{type_of_token}> {tokenizer.token} </{type_of_token}>\n")
                out.seek(0, os.SEEK_END)
                pos = out.tell() - 2
                while pos > 0 and out.read(1) != "\n":
                    pos -= 1
                    out.seek(pos, os.SEEK_SET)
                if pos > 0:
                    out.seek(pos, os.SEEK_SET)
                    out.truncate()
                out.write("</tokens>\n")
                out.close()
                token_file = open(root.replace('.jack', 'T.xml'), 'r+')
                vm_writer = VMWriter(root)
                agent = VM_agent(token_file, vm_writer)
                agent.compile_class()

    else:
        root = sys.argv[1]
        tokenizer = Tokenizer(root)
        out = open(root.replace('.jack', 'T.xml'), 'w+')
        out.write("<tokens>\n")
        while tokenizer.has_more_tokens():
            tokenizer.advance()
            type_of_token = tokenizer.token_type()
            out.write(f"<{type_of_token}> {tokenizer.token} </{type_of_token}>\n")
        out.seek(0, os.SEEK_END)
        pos = out.tell() - 2
        while pos > 0 and out.read(1) != "\n":
            pos -= 1
            out.seek(pos, os.SEEK_SET)
        if pos > 0:
            out.seek(pos, os.SEEK_SET)
            out.truncate()
        out.write("</tokens>\n")
        out.close()
        token_file = open(root.replace('.jack', 'T.xml'), 'r+')
        vm_writer = VMWriter(root)
        agent = VM_agent(token_file, vm_writer)
        agent.compile_class()


if __name__ == "__main__":
    main()