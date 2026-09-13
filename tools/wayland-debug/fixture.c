#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* PRODUCTION_HELPER */

static int unhex(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

int main(int argc, char **argv)
{
    char text[8193];
    struct { struct { const char *s; } args[1]; } value, *closure = &value;
    FILE *f = stdout;
    int i = 0;
    size_t n, j;
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "nil")) {
        closure->args[0].s = NULL;
    } else {
        n = strlen(argv[1]);
        if (n % 2 || n / 2 >= sizeof(text)) return 2;
        for (j = 0; j < n; j += 2) {
            int hi = unhex(argv[1][j]), lo = unhex(argv[1][j + 1]);
            if (hi < 0 || lo < 0) return 2;
            text[j / 2] = (char)((hi << 4) | lo);
        }
        text[n / 2] = 0;
        closure->args[0].s = text;
    }
    fputs("EDITOR_WAYLAND [00:04:22.897519] {Default Queue} -> "
          "zwp_text_input_v3#29.set_surrounding_text(", f);
    switch (0) {
    case 0:
        /* PRODUCTION_CASE */
    }
    fputs(", 7, 7)\n", f);
    return ferror(f) ? 1 : 0;
}
