{
    "name": "OCD Live: Recruitment Of The Hosts",
    "summary": "Job offer of live host in Lome on the website; a hired applicant becomes "
    "a host of the remote lives",
    "version": "20.0.1.0.0",
    "category": "Human Resources/Recruitment",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live", "website_hr_recruitment"],
    "data": [
        "data/hr_job_data.xml",
        "data/hr_recruitment_stage_data.xml",
        "views/ocd_live_recruitment_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ocd_live_recruitment/static/src/**/*",
        ],
    },
    "installable": True,
}
