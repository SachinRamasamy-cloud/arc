"""Linux process resource limits; NOT a substitute for container/seccomp isolation."""
import os,resource,sys
if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(25,25))
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    os.execv(sys.argv[1],[sys.argv[1]])
