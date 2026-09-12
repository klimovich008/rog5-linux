// SPDX-License-Identifier: GPL-2.0
/* Actual regulator accounting and panel power helpers; callback boundaries faulted. */
static struct constraints normal;
struct fixture {
    struct regulator_dev parents[2], rails[2];
    struct regulator upstream[2], consumers[2];
    struct regulator_bulk_data supplies[2];
    struct mipi_dsi_device dsi;
    struct ams678_er2_plus_dsc panel;
};
static bool vote_is(int actual, int expected) { return actual == expected; }
static void fresh(struct fixture *f)
{
    *f = (struct fixture){0};
    for (int i=0;i<2;i++) {
        f->parents[i].constraints = &normal;
        f->upstream[i].rdev = &f->parents[i];
        f->rails[i].constraints = &normal; f->rails[i].supply = &f->upstream[i];
        f->consumers[i].rdev = &f->rails[i];
        f->supplies[i].consumer = &f->consumers[i];
        f->supplies[i].supply = i ? "vdd" : "vddio";
    }
    f->panel.supplies = f->supplies; f->panel.dsi = &f->dsi;
    enable_calls = disable_calls = underflows = 0;
}
static void refuses_retry(struct fixture *f)
{
    int before_on = enable_calls, before_off = disable_calls;
    CHECK(ams678_er2_plus_dsc_power_on(&f->panel) == -EBUSY);
    CHECK(ams678_er2_plus_dsc_power_off(&f->panel) == -EUCLEAN);
    CHECK(enable_calls == before_on && disable_calls == before_off && !underflows);
}
int main(int argc, char **argv)
{
    struct fixture f;
    CHECK(argc == 2); fresh(&f);
    if (!strcmp(argv[1], "cycles")) {
        for (int cycle=0;cycle<5;cycle++) {
            CHECK(!ams678_er2_plus_dsc_power_on(&f.panel));
            for (int i=0;i<2;i++) CHECK(f.consumers[i].enable_count == 1 && f.upstream[i].enable_count == 1 && vote_is(f.panel.supply_vote[i], AMS678_VOTE_HELD));
            CHECK(!ams678_er2_plus_dsc_power_off(&f.panel));
            for (int i=0;i<2;i++) CHECK(!f.consumers[i].enable_count && !f.upstream[i].enable_count && vote_is(f.panel.supply_vote[i], AMS678_VOTE_NONE));
        }
        CHECK(!underflows);
    } else if (strstr(argv[1], "disable")) {
        int rail = !strncmp(argv[1], "vdd-", 4);
        bool parent = strstr(argv[1], "parent") != NULL;
        CHECK(!ams678_er2_plus_dsc_power_on(&f.panel));
        if (parent) f.parents[rail].disable_error = -EIO;
        else f.rails[rail].disable_error = -EIO;
        CHECK(ams678_er2_plus_dsc_power_off(&f.panel) == -EIO);
        CHECK(vote_is(f.panel.supply_vote[rail], AMS678_VOTE_UNKNOWN));
        CHECK(f.consumers[rail].enable_count == (parent ? 0 : 1) && f.upstream[rail].enable_count == 1);
        CHECK(vote_is(f.panel.supply_vote[!rail], AMS678_VOTE_NONE) && !f.consumers[!rail].enable_count && !f.upstream[!rail].enable_count);
        refuses_retry(&f);
    } else if (strstr(argv[1], "enable-unwind")) {
        int rail = !strncmp(argv[1], "vdd-", 4);
        f.rails[rail].enable_error = -EIO; f.parents[rail].disable_error = -EIO;
        CHECK(ams678_er2_plus_dsc_power_on(&f.panel) == -EIO);
        CHECK(vote_is(f.panel.supply_vote[rail], AMS678_VOTE_UNKNOWN) && !f.consumers[rail].enable_count && f.upstream[rail].enable_count == 1);
        /* prepare's existing error label invokes this cleanup helper. */
        CHECK(ams678_er2_plus_dsc_power_off(&f.panel) == -EUCLEAN);
        CHECK(vote_is(f.panel.supply_vote[!rail], AMS678_VOTE_NONE) && !f.consumers[!rail].enable_count && !f.upstream[!rail].enable_count);
        refuses_retry(&f);
    } else if (!strncmp(argv[1], "unknown-", 8)) {
        int rail = !strcmp(argv[1], "unknown-vdd-other-held");
        CHECK(!ams678_er2_plus_dsc_power_on(&f.panel));
        f.panel.supply_vote[rail] = AMS678_VOTE_UNKNOWN;
        CHECK(ams678_er2_plus_dsc_power_off(&f.panel) == -EUCLEAN);
        CHECK(vote_is(f.panel.supply_vote[rail], AMS678_VOTE_UNKNOWN) && f.consumers[rail].enable_count == 1);
        CHECK(vote_is(f.panel.supply_vote[!rail], AMS678_VOTE_NONE) && !f.consumers[!rail].enable_count && !f.upstream[!rail].enable_count);
        refuses_retry(&f);
    } else CHECK(false);
    printf("PASS %s\n", argv[1]); return 0;
}
