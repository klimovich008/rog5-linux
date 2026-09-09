/* Synthetic kernel/device/network endpoints for the sealed BusyBox replay.
 * No physical devices, host proc, host networking or real reboot are exposed.
 * All parsing/file applets execute the supplied, unchanged AArch64 BusyBox. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <arpa/inet.h>
#include <net/if.h>
static int real_nc(void) {
    /* Only called inside bwrap's fresh network namespace. */
    int server=socket(AF_INET,SOCK_STREAM,0);if(server<0)return 102;
    for(int i=1;i<=2;i++) {
        struct ifreq request={0};struct sockaddr_in *addr=(void *)&request.ifr_addr;
        strcpy(request.ifr_name,i==1?"lo":"lo:1");addr->sin_family=AF_INET;
        inet_pton(AF_INET,i==1?"169.254.77.1":"169.254.77.2",&addr->sin_addr);
        if(ioctl(server,SIOCSIFADDR,&request))return 103;
    }
    struct ifreq request={0};strcpy(request.ifr_name,"lo");request.ifr_flags=IFF_UP|IFF_LOOPBACK;
    if(ioctl(server,SIOCSIFFLAGS,&request))return 104;
    struct sockaddr_in address={.sin_family=AF_INET,.sin_port=htons(8079)};
    inet_pton(AF_INET,"169.254.77.1",&address.sin_addr);
    if(bind(server,(void *)&address,sizeof(address)) || listen(server,1))return 105;
    pid_t child=fork();if(child<0)return 106;
    if(!child) {
        close(server);execl("/qemu","/qemu","/lib/ld-musl-aarch64.so.1","/sealed/busybox",
          "nc","-n","-w","1","-s","169.254.77.2","169.254.77.1","8079",NULL);_exit(107);
    }
    alarm(3);
    socklen_t length=sizeof(address);int client=accept(server,(void *)&address,&length);
    if(client<0 || address.sin_addr.s_addr!=inet_addr("169.254.77.2"))return 108;
    FILE *f=fopen("/receipt","wx");if(!f)return 109;char buffer[513];int total=0,n;
    while((n=read(client,buffer,sizeof(buffer)))>0) {
        total+=n;if(total>512)return 110;fwrite(buffer,1,n,f);
    }
    fclose(f);close(client);close(server);int status;
    if(waitpid(child,&status,0)!=child || !WIFEXITED(status))return 111;
    return WEXITSTATUS(status);
}
static int scenario(const char *s) {
    char value[80]={0}; FILE *f=fopen("/scenario","r");
    if(f){fgets(value,sizeof(value),f);fclose(f);} return !strcmp(value,s);
}
#include "stateful.h"
static int stateful(void) {
    char value[80]={0};FILE *f=fopen("/scenario","r");
    if(f){fgets(value,sizeof(value),f);fclose(f);}return !strncmp(value,"stateful-",9);
}
int main(int argc,char **argv) {
    if(strstr(argv[0],"rog5-reboot-bootloader")) {
        FILE *f=fopen("/fallback","w");if(!f)return 90;fputs("requested\n",f);fclose(f);return 0;
    }
    if(argc<2)return 91;
    if(stateful() && !strcmp(argv[1],"timeout"))fixture_log(argc,argv);
    if(stateful() && (!strcmp(argv[1],"mountpoint") || !strcmp(argv[1],"mount") ||
       !strcmp(argv[1],"umount") || !strcmp(argv[1],"losetup") || !strcmp(argv[1],"blockdev")))
        return fixture_endpoint(argc,argv);
    if(!strcmp(argv[1],"uname")){puts("7.1.4-fixture");return 0;}
    if(!strcmp(argv[1],"stat") && argc==5 && !strncmp(argv[4],"/oldsys/dev/sda",15)) {
        if(access(argv[4],F_OK))return 92;
        if(strcmp(argv[2],"-c") || strcmp(argv[3],"%F:%t:%T"))return 92;
        char *end;long minor=strtol(argv[4]+15,&end,10);if(*end)return 93;
        printf("block special file:%x:%lx\n",scenario("wrong-node")?8:259,minor);return 0;
    }
    if(!strcmp(argv[1],"blockdev")) {
        if(argc!=4 || strcmp(argv[2],"--getro") || strncmp(argv[3],"/oldsys/dev/sda",15))return 94;
        puts(scenario("ioctl-writable")?"0":"1");return 0;
    }
    if(!strcmp(argv[1],"nc")) {
        const char *expected[]={"nc","-n","-w","1","-s","169.254.77.2","169.254.77.1","8079"};
        if(argc!=9)return 95;
        for(int i=1;i<9;i++)if(strcmp(argv[i],expected[i-1]))return 95;
        if(scenario("real-netcat"))return real_nc();
        if(scenario("network-hang")){sleep(20);return 96;}
        if(scenario("network-fail"))return 96;
        FILE *f=fopen("/receipt","wx");if(!f)return 97;int c,n=0;
        while((c=getchar())!=EOF){if(++n>512)return 98;fputc(c,f);}fclose(f);return 0;
    }
    if(!strcmp(argv[1],"mountpoint")) {
        return scenario("unclean-shutdown") && argc==4 && !strcmp(argv[3],"/oldroot")?0:1;
    }
    if(!strcmp(argv[1],"mount"))return 0;
    if(!strcmp(argv[1],"umount"))return scenario("unclean-shutdown")?1:0;
    if(!strcmp(argv[1],"sleep")){kill(getppid(),SIGTERM);return 0;}
    if(!strcmp(argv[1],"reboot") || !strcmp(argv[1],"poweroff") || !strcmp(argv[1],"losetup"))return 99;
    char **next=calloc(argc+4,sizeof(char*));if(!next)return 100;
    next[0]="/qemu";next[1]="/lib/ld-musl-aarch64.so.1";next[2]="/sealed/busybox";
    for(int i=1;i<argc;i++)next[i+2]=argv[i];
    execv(next[0],next);perror("qemu");return 101;
}
