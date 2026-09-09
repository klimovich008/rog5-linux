/* Stateful synthetic kernel endpoints. Device nodes are inert major/minor 0:0;
 * this code never opens a block device or invokes a mount/loop/ioctl syscall. */
#include <errno.h>
#include <sys/stat.h>

static const char *old_paths[]={
    "/oldroot/.rog5/root-ro", "/oldroot/.rog5/userdata-ro",
    "/oldroot/.rog5/userdata-rw", "/oldroot/.rog5/state",
    "/oldroot/sys", "/oldroot/proc", "/oldroot/run", "/oldroot/dev"};
static const char *new_paths[]={
    "/oldsys/root-ro", "/oldsys/userdata-ro", "/oldsys/userdata-rw",
    "/oldsys/state", "/oldsys/sys", "/oldsys/proc", "/oldsys/run", "/oldsys/dev"};
struct fixture_state { int mounted[8], moved[8], root, persist, loops[2]; };

static void fixture_abort(void) { perror("stateful fixture"); exit(112); }
static void fixture_log(int argc,char **argv) {
    FILE *f=fopen("/operations","a");if(!f)fixture_abort();
    for(int i=1;i<argc;i++)fprintf(f,"%s%s",i==1?"":" ",argv[i]);
    fputc('\n',f);if(fclose(f))fixture_abort();
}
static void fixture_load(struct fixture_state *s) {
    FILE *f=fopen("/mount-state","rb");
    if(!f) {
        if(errno!=ENOENT)fixture_abort();
        memset(s,0,sizeof(*s));for(int i=0;i<8;i++)s->mounted[i]=1;
        s->root=s->loops[0]=1;
        int journal=scenario("stateful-journal-entry") || scenario("stateful-order-overlay-reference");
        s->persist=s->loops[1]=!(scenario("stateful-stopped-state") || journal);
        if(journal)s->mounted[0]=s->mounted[1]=s->mounted[3]=0;
        return;
    }
    if(fread(s,sizeof(*s),1,f)!=1 || fgetc(f)!=EOF)fixture_abort();
    if(fclose(f))fixture_abort();
}
static void fixture_save(struct fixture_state *s) {
    FILE *f=fopen("/mount-state","wb");if(!f)fixture_abort();
    if(fwrite(s,sizeof(*s),1,f)!=1 || fclose(f))fixture_abort();
    f=fopen("/oldsys/proc/self/mountinfo","w");if(!f)fixture_abort();
    fputs("1 0 0:1 / / rw - tmpfs tmpfs rw\n",f);
    const char *types[]={"ext4","ext4","ext4","ext4","sysfs","proc","tmpfs","devtmpfs"};
    const char *devices[]={"259:24","259:58","259:58","7:0","0:3","0:2","0:5","0:4"};
    for(int i=0;i<8;i++)if(s->mounted[i])
        fprintf(f,"%d 1 %s / %s rw - %s fixture rw\n",i+2,devices[i],
                s->moved[i]?new_paths[i]:old_paths[i],types[i]);
    if(s->root)fputs("20 1 0:91 / /oldroot rw - overlay overlay rw\n",f);
    if(s->persist)fputs("21 20 7:1 / /oldroot/persist rw - ext4 fixture rw\n",f);
    /* Model systemd's retained API bind and devtmpfs child copies. */
    fputs("30 1 0:4 / /dev rw - devtmpfs devtmpfs rw\n"
          "31 30 0:35 / /dev/hugepages rw - hugetlbfs hugetlbfs rw\n",f);
    if(s->mounted[7])fprintf(f,"32 9 0:35 / %s/hugepages rw - hugetlbfs hugetlbfs rw\n",
                            s->moved[7]?new_paths[7]:old_paths[7]);
    if(fclose(f))fixture_abort();
}
static int fixture_mount_index(struct fixture_state *s,const char *path) {
    for(int i=0;i<8;i++)if(s->mounted[i] && !strcmp(path,s->moved[i]?new_paths[i]:old_paths[i]))return i;
    return -1;
}
static int fixture_endpoint(int argc,char **argv) {
    struct fixture_state s;fixture_load(&s);fixture_log(argc,argv);
    fixture_save(&s);
    if(!strcmp(argv[1],"mountpoint")) {
        if(argc!=4 || strcmp(argv[2],"-q"))return 113;
        if(!strcmp(argv[3],"/oldroot"))return !s.root;
        if(!strcmp(argv[3],"/oldroot/persist"))return !s.persist;
        return fixture_mount_index(&s,argv[3])<0;
    }
    if(!strcmp(argv[1],"mount")) {
        if(argc==5 && !strcmp(argv[2],"-o") && !strcmp(argv[3],"remount,rw") && !strcmp(argv[4],"/"))return 0;
        if(argc!=5 || strcmp(argv[2],"--move"))return 113;
        int i=fixture_mount_index(&s,argv[3]);
        if(i<0 || s.moved[i] || strcmp(argv[4],new_paths[i]))return 113;
        if(scenario("stateful-move-fail") && i==2)return 1;
        s.moved[i]=1;fixture_save(&s);return 0;
    }
    if(!strcmp(argv[1],"umount")) {
        int lazy=argc==4 && !strcmp(argv[2],"-l");
        if(argc!=3 && !lazy)return 113;
        const char *path=argv[argc-1];
        if(!strcmp(path,"/oldroot")) {
            if(!lazy) {
                if(scenario("stateful-root-busy") || s.persist)return 1;
                for(int i=0;i<8;i++)if(s.mounted[i] && !s.moved[i])return 1;
            }
            s.root=0;
        } else if(!strcmp(path,"/oldroot/persist"))s.persist=0;
        else {
            int i=fixture_mount_index(&s,path);if(i<0)return 113;
            if(!lazy && ((i==3 && s.root) || (i==2 && (s.loops[0] || s.loops[1]))))return 1;
            s.mounted[i]=0;
        }
        fixture_save(&s);return 0;
    }
    if(!strcmp(argv[1],"losetup")) {
        int detach=argc==4 && !strcmp(argv[2],"-d");
        if(argc!=3 && !detach)return 113;
        const char *path=argv[argc-1];int i;
        if(!strcmp(path,"/oldsys/dev/loop0"))i=0;
        else if(!strcmp(path,"/oldsys/dev/loop1"))i=1;
        else return 113;
        if(!detach)return !s.loops[i];
        if(!s.loops[i] || (i==0?(s.mounted[3] || s.root):s.persist))return 1;
        if(i==0 && scenario("stateful-detach-fail"))return 1;
        if(i==0 && scenario("stateful-detach-lies"))return 0;
        char backing[128],directory[128];
        snprintf(directory,sizeof(directory),"/oldsys/sys/class/block/loop%d/loop",i);
        snprintf(backing,sizeof(backing),"/oldsys/sys/class/block/loop%d/loop/backing_file",i);
        if(unlink(backing) || rmdir(directory))fixture_abort();
        s.loops[i]=0;fixture_save(&s);return 0;
    }
    if(!strcmp(argv[1],"blockdev")) {
        if(argc!=4 || strncmp(argv[3],"/oldsys/dev/sda",15))return 113;
        char *end;long i=strtol(argv[3]+15,&end,10);
        if(*end || i<0 || i>=117)return 113;
        char path[128];snprintf(path,sizeof(path),"/oldsys/sys/class/block/sda%s/ro",argv[3]+15);
        if(!strcmp(argv[2],"--getro")) {
            FILE *f=fopen(path,"r");if(!f)fixture_abort();int c=fgetc(f);fclose(f);putchar(c);putchar('\n');return 0;
        }
        if(strcmp(argv[2],"--setro"))return 113;
        if(s.root || s.mounted[2] || s.mounted[3] || s.persist || s.loops[0] || s.loops[1])return 1;
        if(i==23 && scenario("stateful-relock-fail"))return 1;
        FILE *f=fopen(path,"w");if(!f)fixture_abort();fputs("1\n",f);if(fclose(f))fixture_abort();return 0;
    }
    return 113;
}
