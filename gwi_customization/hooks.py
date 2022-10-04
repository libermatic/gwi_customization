# -*- coding: utf-8 -*-
from . import __version__

app_name = "gwi_customization"
app_version = __version__
app_title = "GWI Customization"
app_publisher = "Libermatic"
app_description = "Customizations for GWI"
app_icon = "fa fa-university"
app_color = "#8BC34A"
app_email = "info@libermatic.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/css/gwi_customization.css"
app_include_js = "gwi_customization.bundle.js"

# include js, css files in header of web template
# web_include_css = "/assets/gwi_customization/css/gwi_customization.css"
# web_include_js = "/assets/gwi_customization/js/gwi_customization.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#    "Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "gwi_customization.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "gwi_customization.install.before_install"
# after_install = "gwi_customization.install.after_install"
setup_wizard_complete = "gwi_customization.install.after_wizard_complete"


# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = \
#    "gwi_customization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#     "Event":
#        "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#     "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Customer": {
        "on_update": "gwi_customization.microfinance.doctype.microfinance_loanee.microfinance_loanee.on_customer_update"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {"monthly": ["gwi_customization.tasks.monthly"]}

# Testing
# -------

before_tests = "gwi_customization.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
#     "frappe.desk.doctype.event.event.get_events":
#        "gwi_customization.event.get_events"
# }
