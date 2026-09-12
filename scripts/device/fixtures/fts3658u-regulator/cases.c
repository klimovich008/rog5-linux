// SPDX-License-Identifier: GPL-2.0
/* Expected consumer behavior; provider accounting runs actual kernel code. */
static bool vote_is(int actual, int expected) { return actual == expected; }
static struct constraints normal, always = { .always_on=true };
static struct i2c_client client;
struct fixture {
    struct regulator_dev bob, l3, l8;
    struct regulator parent, vdd, io;
    struct rog5_fts touch;
};
static void fresh(struct fixture *f)
{
    *f = (struct fixture){0};
    f->bob.constraints = &normal;
    f->parent.rdev = &f->bob;
    f->l3.constraints = &normal; f->l3.supply = &f->parent;
    f->vdd.rdev = &f->l3;
    f->l8.constraints = &always; f->l8.use_count = 1;
    f->io.rdev = &f->l8;
    f->touch.client = &client; f->touch.vdd = &f->vdd; f->touch.vcc_i2c = &f->io;
    disable_calls = enable_calls = underflows = 0;
}
static void refuses_retry(struct fixture *f)
{
    int off_calls = disable_calls, on_calls = enable_calls;
    CHECK(rog5_fts_power_on(&f->touch) == -EBUSY);
    CHECK(rog5_fts_power_off(&f->touch) == -EUCLEAN);
    CHECK(disable_calls == off_calls && enable_calls == on_calls && !underflows);
}
int main(int argc, char **argv)
{
    struct fixture f;
    CHECK(argc == 2);
    fresh(&f);
    if (!strcmp(argv[1], "cycles")) {
        for (int i=0;i<5;i++) {
            CHECK(!rog5_fts_power_on(&f.touch));
            CHECK(vote_is(f.touch.vdd_vote, ROG5_FTS_VOTE_HELD) && vote_is(f.touch.io_vote, ROG5_FTS_VOTE_HELD));
            CHECK(f.vdd.enable_count == 1 && f.parent.enable_count == 1 && f.io.enable_count == 1);
            CHECK(!rog5_fts_power_off(&f.touch));
            CHECK(vote_is(f.touch.vdd_vote, ROG5_FTS_VOTE_NONE) && vote_is(f.touch.io_vote, ROG5_FTS_VOTE_NONE));
            CHECK(!f.vdd.enable_count && !f.parent.enable_count && !f.io.enable_count && f.l8.use_count == 1);
        }
        CHECK(!underflows);
    } else if (!strcmp(argv[1], "child-disable") || !strcmp(argv[1], "parent-disable")) {
        bool parent = !strcmp(argv[1], "parent-disable");
        CHECK(!rog5_fts_power_on(&f.touch));
        if (parent) f.bob.disable_error = -EIO; else f.l3.disable_error = -EIO;
        CHECK(rog5_fts_power_off(&f.touch) == -EIO);
        CHECK(vote_is(f.touch.vdd_vote, ROG5_FTS_VOTE_UNKNOWN));
        CHECK(f.vdd.enable_count == (parent ? 0 : 1) && f.parent.enable_count == 1);
        CHECK(vote_is(f.touch.io_vote, ROG5_FTS_VOTE_NONE) && !f.io.enable_count);
        refuses_retry(&f);
    } else if (!strcmp(argv[1], "enable-unwind") || !strcmp(argv[1], "enable-failure")) {
        bool parent = !strcmp(argv[1], "enable-unwind");
        if (parent) f.bob.disable_error = -EIO;
        f.l3.enable_error = -EIO;
        CHECK(rog5_fts_power_on(&f.touch) == -EIO);
        CHECK(vote_is(f.touch.vdd_vote, ROG5_FTS_VOTE_UNKNOWN) && !f.vdd.enable_count);
        CHECK(f.parent.enable_count == (parent ? 1 : 0));
        CHECK(vote_is(f.touch.io_vote, ROG5_FTS_VOTE_NONE) && !f.io.enable_count);
        refuses_retry(&f);
    } else if (!strcmp(argv[1], "unknown-other-held")) {
        CHECK(!rog5_fts_power_on(&f.touch));
        /* Unknown IO ownership must not prevent release of the known VDD vote. */
        f.touch.io_vote = ROG5_FTS_VOTE_UNKNOWN;
        CHECK(rog5_fts_power_off(&f.touch) == -EUCLEAN);
        CHECK(vote_is(f.touch.vdd_vote, ROG5_FTS_VOTE_NONE) && !f.vdd.enable_count && !f.parent.enable_count);
        CHECK(vote_is(f.touch.io_vote, ROG5_FTS_VOTE_UNKNOWN) && f.io.enable_count == 1);
        refuses_retry(&f);
    } else CHECK(false);
    printf("PASS %s\n", argv[1]);
    return 0;
}
