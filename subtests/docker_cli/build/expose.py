import os
from dockertest.networking import PortContainer
from dockertest.output import mustpass
from dockertest.output import wait_for_output
from dockertest.dockercmd import AsyncDockerCmd
from dockertest.dockercmd import DockerCmd
from build import build_base


class expose(build_base):

    def initialize(self):
        super(expose, self).initialize()
        self.sub_stuff['fds'] = []
        self.sub_stuff['async_dkrcmd'] = None
        self.sub_stuff['port_cntnr'] = None

    def start_test_container(self, read_fd, write_fd):
        dc = self.sub_stuff['dc']
        name = dc.get_unique_name()
        subargs = ['--interactive', '--publish-all',
                   '--name', name, self.sub_stuff['builds'][-1].image_name,
                   'sh']
        async_dkrcmd = AsyncDockerCmd(self, 'run', subargs)
        self.sub_stuff['async_dkrcmd'] = async_dkrcmd
        async_dkrcmd.execute(read_fd)
        os.close(read_fd)
        os.write(write_fd, 'echo "StArTeD!"\n')
        self.failif(not wait_for_output(lambda: async_dkrcmd.stdout,
                                        "StArTeD!",
                                        timeout=10), str(async_dkrcmd))
        return name

    def container_ports(self, name):
        port_dkrcmd = DockerCmd(self, 'port', [name])
        port_dkrcmd.execute()
        mustpass(port_dkrcmd)
        return port_dkrcmd.stdout.strip()

    def run_once(self):
        super(expose, self).run_once()
        read_fd, write_fd = os.pipe()
        self.sub_stuff['fds'] += [read_fd, write_fd]
        name = self.start_test_container(read_fd, write_fd)
        portstr = self.container_ports(name)
        component = PortContainer.split_to_component(portstr)
        self.sub_stuff['port_cntnr'] = PortContainer(*component)
        os.write(write_fd, 'exit\n')
        dc = self.sub_stuff['dc']
        dc.wait_by_name(name)
        dc.remove_by_name(name)

    def postprocess(self):
        super(expose, self).postprocess()
        cntnr_port = self.sub_stuff['port_cntnr']
        self.failif(cntnr_port.host_port != 8080, str(cntnr_port))
        self.failif(cntnr_port.protocol != 'tcp', str(cntnr_port))

    def cleanup(self):
        for fd in self.sub_stuff.get('fds', []):
            try:
                os.close(fd)
            except OSError:
                pass
        super(expose, self).cleanup()
