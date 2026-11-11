def post_init_hook(env):
    env["website"]._ocd_setup_site()
    env["res.country"]._ocd_set_default_offered()
