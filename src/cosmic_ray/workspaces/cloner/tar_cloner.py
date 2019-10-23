import os
from logging import getLogger
from subprocess import Popen, PIPE

from cosmic_ray.execution_engines.local_execution_engine import \
    execution_engines_cloning_config
from cosmic_ray.workspaces.cloner import Cloner


log = getLogger(__name__)


class TarCloner(Cloner):

    @classmethod
    def prepare_local_side(cls):
        re_exclude = execution_engines_cloning_config['ignore-files']
        re_exclude = '|'.join('(.*/|)%s' % s for s in re_exclude)

        p1 = Popen(('find',
                    '(', '-regextype', 'posix-extended', '-regex', re_exclude, '-prune', ')',
                    '-o', '-type', 'f', '-print0'), stdout=PIPE)

        p2 = Popen(('tar', 'czf', '-',
                    '--verbatim-files-from', '--null', '-T', '-'),
                   stdin=p1.stdout, stdout=PIPE)

        data = p2.stdout.read()
        ret1 = p1.wait()
        ret2 = p2.wait()
        if ret1 != 0:
            raise Exception("Problem when finding files: %s" % ret1)
        if ret2 != 0:
            raise Exception("Problem when tarring: %s" % ret2)

        return data

    def load_prepared_data(self, prepared_data):
        self.tar = prepared_data

    def clone(self, dest_path):
        os.makedirs(dest_path, exist_ok=True)
        log.info("untar file in %s", dest_path)

        with open(os.path.join(dest_path, 'in.tgz'), 'wb') as f:
            f.write(self.tar)

        p = Popen(('tar', 'xzfC', '-', dest_path), stdin=PIPE)
        tar = self.tar
        while tar:
            tar = tar[p.stdin.write(tar):]
        p.stdin.close()
        ret = p.wait()
        if ret != 0:
            raise Exception('untar failed: %s' % ret)
