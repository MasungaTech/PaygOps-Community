

from os import chmod
import sys
import time
import stat
from config import MIGRATIONS_DIR
from os.path import exists


def create_migration(name):

    version = int(time.time())

    file_name = '{}{}_{}.py'.format(MIGRATIONS_DIR, version, name)
    template = "from pony.orm import db_session\n\n" \
            "@db_session\ndef up(db):\n    pass\n\n" \
            "@db_session\ndef down(db):\n    pass\n"

    with open(file_name, 'w+') as f:
        f.write(template)

    if exists(file_name):
        chmod(file_name, stat.S_IRWXO)
        print('Migration file {} was created.'.format(file_name.replace('/crm/', '', 1)))

if __name__ == '__main__':
    create_migration(sys.argv[1])