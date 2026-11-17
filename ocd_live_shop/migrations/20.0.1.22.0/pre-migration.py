def migrate(cr, version):
    """The alerts of a boutique have a kind (the next live, the return from holiday): one alert
    waiting per contact, vendor and kind. The index of before (per contact and vendor) would
    refuse an alert of return next to an alert of live."""
    cr.execute("DROP INDEX IF EXISTS ocd_boutique_alert_unique_waiting")
