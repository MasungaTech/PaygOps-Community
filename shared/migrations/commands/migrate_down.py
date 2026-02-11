import sys
from shared.migrations.commands.migrate import down


if __name__ == '__main__':
    down(sys.argv[1])