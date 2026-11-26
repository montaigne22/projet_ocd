"""Le coût des écrans de l'équipe et des actions planifiées sur une base (docs/RAPPORT_DE_CHARGE.md,
partie 9) : pour chacun, le nombre de requêtes à la base et le temps, comme un vrai appel (une
transaction neuve, rien en mémoire). Les actions planifiées tournent pour de vrai : seulement sur
une copie de la démo (le script refuse une base sans ocd_live_demo).

    odoo-bin shell -c odoo.conf -d ocd_volume --no-http < tools/charge/requetes.py

À lancer sur la démo puis sur la démo grossie (tools/charge/volume.py) : ce qui grandit avec les
données se voit d'une colonne à l'autre.
"""
# ruff: noqa: F821 (env est donné par le shell d'Odoo)
import os
import time

if not env["ir.module.module"].search_count([("name", "=", "ocd_live_demo"), ("state", "=", "installed")]):
    raise SystemExit("Refusé : cette base n'a pas la démo d'OCD Live (les actions planifiées y tourneraient).")

admin = env.ref("base.user_admin")
team = env(user=admin)


def measure(label, function):
    env.cr.rollback()
    env.invalidate_all()
    start_count, start = env.cr.sql_log_count, time.time()
    try:
        function()
        result = ""
    except Exception as error:  # noqa: BLE001 (un écran absent de cette base, une action en erreur)
        result = f"  ({type(error).__name__}: {str(error)[:80]})"
    print(f"REQUETES {label:<62} {env.cr.sql_log_count - start_count:6d} requêtes {(time.time() - start) * 1000:8.0f} ms{result}", flush=True)


screens = [
    ("Tableau de bord", "ocd.live.dashboard", "get_dashboard_data", ()),
    ("Réservations", "ocd.live.planning", "get_planning_data", (False,)),
    ("À vérifier", "ocd.live.verification", "get_verification_data", ()),
    ("Automatisations", "ocd.automation", "get_automations_page", ()),
    ("Paramètres", "ocd.live.settings", "get_settings_page", ()),
    ("Dispatch", "ocd.live.dispatch", "get_dispatch_data", ()),
    ("Commandes", "ocd.live.orders", "get_orders_data", ()),
    ("Livreurs", "ocd.live.couriers", "get_couriers_data", ()),
    ("Régie", "ocd.live.regie", "get_regie_data", (False,)),
    ("Conversations WhatsApp", "ocd.whatsapp.inbox", "get_inbox", (None, {})),
]
for label, model, method, args in screens:
    if model in team:
        measure(f"écran · {label}", lambda: getattr(team[model], method)(*args))

if os.environ.get("CRONS", "1") != "0":
    crons = env["ir.cron"].sudo().search([("active", "=", True)])
    modules = {data.res_id: data.module for data in env["ir.model.data"].sudo().search([("model", "=", "ir.cron"), ("res_id", "in", crons.ids)])}
    for cron in crons.sorted("id"):
        module = modules.get(cron.id, "")
        if not (module.startswith("ocd_") or module.startswith("whatsapp_cloud") or module == "attachment_s3"):
            continue
        action = cron.ir_actions_server_id.sudo()
        measure(f"tâche · {cron.name[:52]}", lambda: (action.with_user(cron.user_id).run(), env.cr.commit()))
