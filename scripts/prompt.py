import os

from cmd import Cmd
 
class EnvoxyPrompt(Cmd):
    prompt = 'envoxy> '
    intro = 'Welcome to Envoxy Prompt! Type ? to list commands'
    last_output = ''
    dir_path = os.path.dirname(os.path.realpath(__file__))
 
    def do_exit(self, inp):
        print("Bye")
        return True
    
    def help_exit(self):
        print('Exit the application. Shorthand: x q Ctrl-D.')

    def do_exec(self, line):
        "Run a shell command: exec [cmd]"
        print("running shell command: {}".format(line))
        output = os.popen(line).read()
        print(output)
        self.last_output = output

    def do_python(self, inp):
        "Run a python interactive shell command: python"
        print("running python interactive shell")

        output = os.popen(' && '.join([
            'PYTHONSTARTUP={}/prompt_init.py', 
            '. /opt/envoxy/bin/activate', 
            'python3.6', 
            'deactivate'
        ]).format(self.dir_path)).read()
        
        print(output)
        self.last_output = output
    
    def do_echo(self, line):
        "Print the input, replacing '$out' with the output of the last shell command"
        # Obviously not robust
        print(line.replace('$out', self.last_output))
 
    def default(self, inp):
        if inp == ':x' or inp == ':q':
            return self.do_exit(inp)
 
        print("Default: {}".format(inp))
 
    do_EOF = do_exit
    help_EOF = help_exit
 
if __name__ == '__main__':
    EnvoxyPrompt().cmdloop()