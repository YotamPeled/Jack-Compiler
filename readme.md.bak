Nand To Teris Project 11,
Full scale Jack compiler. 
Output of the program is VM code designed to run on a virtual machine implemented previously in the Nand To Teris course.

The implementation steps:
 - Tokenizizer
A basic service of any syntax analyzer, is the act of breaking a given textual input into a stream of tokens. And while it is at it, the tokenizer can also classify the tokens into lexical categories.

-Parser: Compilation Engine
In the context of this project, parsing is defined narrowly as the act of going over the tokenized input and rendering its grammatical structure using some agreed-upon format. The specific parser that we implement here is based on the Jack grammar and is designed to emit XML output. 
The Jack parser is implemented by the Compilation Engine module, whose API is given during the course.
- Symbol Table
 Building the compiler's symbol table module and using it to extend the syntax analyser. Presently, whenever an identifier is encountered in the source code, say foo, the syntax analyser outputs the XML line "<identifier> foo </identifier>". Instead, have your analyser output the following information as part of its XML output (using some output format of your choice):

- Code Generation
Generate the final VM code after compilation
