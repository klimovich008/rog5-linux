/* Synthetic kernel/device/network endpoints for the sealed BusyBox replay.
 * No physical devices, host proc, host networking or real reboot are exposed.
 * Normal parsing/file applets execute the supplied, unchanged AArch64 BusyBox.
 * Explicit mount-awk fault cases replace only that invocation's outcome. */
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
static int save_frame(const char *buffer,int length) {
    char path[64]="/receipt";
    const char *prefix="format=rog5-source-teardown-diagnostic-v2\n";
    if(length>=(int)strlen(prefix) && !memcmp(buffer,prefix,strlen(prefix))) {
        int i;for(i=0;i<6;i++) {
            snprintf(path,sizeof(path),"/diagnostic-%d",i);
            if(access(path,F_OK))break;
        }
        if(i==6)return 114;
    }
    FILE *f=fopen(path,"wx");if(!f)return 97;
    if(fwrite(buffer,1,length,f)!=(size_t)length || fclose(f))return 115;
    return 0;
}
static int setup_network(int server) {
    /* Only called inside bwrap's fresh network namespace. */
    for(int i=1;i<=2;i++) {
        struct ifreq request={0};struct sockaddr_in *addr=(void *)&request.ifr_addr;
        strcpy(request.ifr_name,i==1?"lo":"lo:1");addr->sin_family=AF_INET;
        inet_pton(AF_INET,i==1?"169.254.77.1":"169.254.77.2",&addr->sin_addr);
        if(ioctl(server,SIOCSIFADDR,&request))return 103;
    }
    struct ifreq request={0};strcpy(request.ifr_name,"lo");request.ifr_flags=IFF_UP|IFF_LOOPBACK;
    if(ioctl(server,SIOCSIFFLAGS,&request))return 104;
    return 0;
}
static int real_nc(void) {
    int server=socket(AF_INET,SOCK_STREAM,0);if(server<0)return 102;
    int reuse=1;if(setsockopt(server,SOL_SOCKET,SO_REUSEADDR,&reuse,sizeof(reuse)))return 102;
    int setup=setup_network(server);if(setup)return setup;
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
    char buffer[513];int total=0,n;
    while((n=read(client,buffer+total,sizeof(buffer)-total))>0) {
        total+=n;if(total>512)return 110;
    }
    int saved=save_frame(buffer,total);if(saved)return saved;
    close(client);close(server);int status;
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
    if(!strcmp(argv[1],"awk") && !strcmp(argv[argc-1],"/oldsys/proc/self/mountinfo")) {
        if(scenario("mount-awk-error")){fputs("fixture input error\n",stderr);return 2;}
        if(scenario("mount-awk-output")){puts("unexpected fixture output");return 0;}
        if(scenario("mount-awk-end-error")) {
            fputs("fixture input error\n",stderr);puts("mount-missing:root");return 1;
        }
        if(scenario("mount-awk-hang")){sleep(20);return 1;}
    }
    if(!strcmp(argv[1],"fixture-network") && scenario("receiver-poll")) {
        int s=socket(AF_INET,SOCK_STREAM,0);if(s<0)return 102;
        int result=setup_network(s);close(s);return result;
    }
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
        int attempts=0,c;FILE *log=fopen("/nc-attempts","r");
        if(log){while((c=fgetc(log))!=EOF)if(c=='\n')attempts++;fclose(log);}
        log=fopen("/nc-attempts","a");if(!log)return 116;
        fputs("attempt\n",log);if(fclose(log))return 116;attempts++;
        if(scenario("receiver-poll"))goto execute_applet;
        if(scenario("real-netcat"))return real_nc();
        if(scenario("diagnostic-hang") && attempts==2){sleep(20);return 96;}
        if(scenario("network-hang")){sleep(20);return 96;}
        if(scenario("network-fail"))return 96;
        char buffer[512];int n=0;
        while((c=getchar())!=EOF){if(n==512)return 98;buffer[n++]=(char)c;}
        return save_frame(buffer,n);
    }
    if(!strcmp(argv[1],"mountpoint")) {
        return scenario("unclean-shutdown") && argc==4 && !strcmp(argv[3],"/oldroot")?0:1;
    }
    if(!strcmp(argv[1],"mount"))return 0;
    if(!strcmp(argv[1],"umount"))return scenario("unclean-shutdown")?1:0;
    if(!strcmp(argv[1],"sleep")){kill(getppid(),SIGTERM);return 0;}
    if(!strcmp(argv[1],"reboot") || !strcmp(argv[1],"poweroff") || !strcmp(argv[1],"losetup"))return 99;
execute_applet: ;
    char **next=calloc(argc+4,sizeof(char*));if(!next)return 100;
    next[0]="/qemu";next[1]="/lib/ld-musl-aarch64.so.1";next[2]="/sealed/busybox";
    for(int i=1;i<argc;i++)next[i+2]=argv[i];
    execv(next[0],next);perror("qemu");return 101;
}
