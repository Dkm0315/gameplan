# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.query_builder.functions import Count
from frappe.utils import split_emails, strip_html, validate_email_address

import gameplan
from gameplan.utils import validate_type


@frappe.whitelist(allow_guest=True)
def get_user_info(user=None):
	if frappe.session.user == "Guest":
		frappe.throw("Authentication failed", exc=frappe.AuthenticationError)

	filters = {"roles.role": ["like", "Gameplan %"]}
	if user:
		filters["name"] = user

	users = frappe.qb.get_query(
		"User",
		filters=filters,
		fields=["name", "email", "enabled", "user_image", "full_name", "user_type"],
		order_by="full_name asc",
		distinct=True,
	).run(as_dict=1)

	# Get discussion counts for last 3 months
	Discussion = frappe.qb.DocType("GP Discussion")
	discussion_counts = (
		frappe.qb.from_(Discussion)
		.select(Discussion.owner, Count(Discussion.name).as_("count"))
		.where(Discussion.creation >= frappe.utils.add_months(frappe.utils.now(), -3))
		.where(Discussion.owner.isin([u.name for u in users]))
		.groupby(Discussion.owner)
	).run(as_dict=1)
	discussion_count_map = {d.owner: d.count for d in discussion_counts}

	# Get comment counts for last 3 months
	Comment = frappe.qb.DocType("GP Comment")
	comment_counts = (
		frappe.qb.from_(Comment)
		.select(Comment.owner, Count(Comment.name).as_("count"))
		.where(Comment.creation >= frappe.utils.add_months(frappe.utils.now(), -3))
		.where(Comment.owner.isin([u.name for u in users]))
		.groupby(Comment.owner)
	).run(as_dict=1)
	comment_count_map = {c.owner: c.count for c in comment_counts}

	roles = frappe.db.get_all("Has Role", filters={"parenttype": "User"}, fields=["role", "parent"])
	user_profiles = frappe.db.get_all(
		"GP User Profile",
		fields=["user", "name", "image", "image_background_color", "is_image_background_removed", "bio"],
		filters={"user": ["in", [u.name for u in users]]},
	)
	user_profile_map = {u.user: u for u in user_profiles}
	for user in users:
		if frappe.session.user == user.name:
			user.session_user = True
		user_profile = user_profile_map.get(user.name)
		if user_profile:
			user.user_profile = user_profile.name
			user.user_image = user_profile.image
			user.image_background_color = user_profile.image_background_color
			user.is_image_background_removed = user_profile.is_image_background_removed
			user.bio = user_profile.bio
		user_roles = [r.role for r in roles if r.parent == user.name]
		user.role = None
		for role in ["Gameplan Guest", "Gameplan Member", "Gameplan Admin"]:
			if role in user_roles:
				user.role = role

		# Add discussion and comment counts
		user.discussions_count_3m = discussion_count_map.get(user.name, 0)
		user.comments_count_3m = comment_count_map.get(user.name, 0)

	return users


@frappe.whitelist()
@validate_type
def change_user_role(user: str, role: str):
	if gameplan.is_guest():
		frappe.throw("Only Admin can change user roles")

	if role not in ["Gameplan Guest", "Gameplan Member", "Gameplan Admin"]:
		return get_user_info(user)[0]

	user_doc = frappe.get_doc("User", user)
	for _role in user_doc.roles:
		if _role.role in ["Gameplan Guest", "Gameplan Member", "Gameplan Admin"]:
			user_doc.remove(_role)
	user_doc.append_roles(role)
	user_doc.save(ignore_permissions=True)

	return get_user_info(user)[0]


@frappe.whitelist()
@validate_type
def remove_user(user: str):
	user_doc = frappe.get_doc("User", user)
	user_doc.enabled = 0
	user_doc.save(ignore_permissions=True)
	return user


@frappe.whitelist()
@validate_type
def invite_by_email(emails: str, role: str, projects: list = None):
	if not emails:
		return
	email_string = validate_email_address(emails, throw=False)
	email_list = split_emails(email_string)
	if not email_list:
		return
	existing_members = frappe.db.get_all("User", filters={"email": ["in", email_list]}, pluck="email")
	existing_invites = frappe.db.get_all(
		"GP Invitation",
		filters={
			"email": ["in", email_list],
			"role": ["in", ["Gameplan Admin", "Gameplan Member"]],
		},
		pluck="email",
	)

	if role == "Gameplan Guest":
		to_invite = list(set(email_list) - set(existing_invites))
	else:
		to_invite = list(set(email_list) - set(existing_members) - set(existing_invites))

	if projects:
		projects = frappe.as_json(projects, indent=None)

	for email in to_invite:
		frappe.get_doc(doctype="GP Invitation", email=email, role=role, projects=projects).insert(
			ignore_permissions=True
		)


@frappe.whitelist()
def unread_notifications():
	return frappe.db.count(
		"GP Notification",
		filters={"to_user": frappe.session.user, "read": 0},
	)


@frappe.whitelist(allow_guest=True)
@validate_type
def accept_invitation(key: str = None):
	if not key:
		frappe.throw("Invalid or expired key")

	result = frappe.db.get_all("GP Invitation", filters={"key": key}, pluck="name")
	if not result:
		frappe.throw("Invalid or expired key")

	invitation = frappe.get_doc("GP Invitation", result[0])

	invitation.accept()
	invitation.reload()

	user = frappe.get_doc("User", invitation.email)
	needs_password_setup = user and not user.last_password_reset_date

	if invitation.status == "Accepted":
		if needs_password_setup:
			url = invitation.get_password_link()
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = f"{url}"
		else:
			frappe.local.login_manager.login_as(invitation.email)
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = "/g"


@frappe.whitelist()
def get_unsplash_photos(keyword=None):
	from gameplan.unsplash import get_by_keyword, get_list

	if keyword:
		return get_by_keyword(keyword)

	return frappe.cache().get_value("unsplash_photos", generator=get_list)


@frappe.whitelist()
def get_unread_items():
	Discussion = frappe.qb.DocType("GP Discussion")
	Visit = frappe.qb.DocType("GP Discussion Visit")
	query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.team, Count(Discussion.team).as_("count"))
		.left_join(Visit)
		.on((Visit.discussion == Discussion.name) & (Visit.user == frappe.session.user))
		.where((Visit.last_visit.isnull()) | (Visit.last_visit < Discussion.last_post_at))
		.groupby(Discussion.team)
	)

	is_guest = gameplan.is_guest()
	if is_guest:
		GuestAccess = frappe.qb.DocType("GP Guest Access")
		project_list = GuestAccess.select(GuestAccess.project).where(GuestAccess.user == frappe.session.user)
		query = query.where(Discussion.project.isin(project_list))

	# pypika doesn't have any API for "FORCE INDEX FOR JOIN"
	sql = query.get_sql()
	sql = sql.replace(
		"LEFT JOIN `tabGP Discussion Visit`",
		"LEFT JOIN `tabGP Discussion Visit` FORCE INDEX FOR JOIN(discussion_user_index)",
	)
	data = frappe.db.sql(sql, as_dict=1)

	out = {}
	for d in data:
		out[d.team] = d.count
	return out


@frappe.whitelist()
def get_unread_items_by_project(projects):
	from frappe.query_builder.functions import Count

	project_names = frappe.parse_json(projects)
	Discussion = frappe.qb.DocType("GP Discussion")
	Visit = frappe.qb.DocType("GP Discussion Visit")
	query = (
		frappe.qb.from_(Discussion)
		.select(Discussion.project, Count(Discussion.project).as_("count"))
		.left_join(Visit)
		.on((Visit.discussion == Discussion.name) & (Visit.user == frappe.session.user))
		.where((Visit.last_visit.isnull()) | (Visit.last_visit < Discussion.last_post_at))
		.where(Discussion.project.isin(project_names))
		.groupby(Discussion.project)
	)

	data = query.run(as_dict=1)
	out = {}
	for d in data:
		out[d.project] = d.count
	return out


@frappe.whitelist()
def mark_all_notifications_as_read():
	for d in frappe.db.get_all(
		"GP Notification",
		filters={"to_user": frappe.session.user, "read": 0},
		pluck="name",
	):
		doc = frappe.get_doc("GP Notification", d)
		doc.read = 1
		doc.save(ignore_permissions=True)


@frappe.whitelist()
def recent_projects():
	from frappe.query_builder.functions import Max

	ProjectVisit = frappe.qb.DocType("GP Project Visit")
	Team = frappe.qb.DocType("GP Team")
	Project = frappe.qb.DocType("GP Project")
	Pin = frappe.qb.DocType("GP Pinned Project")
	pinned_projects_query = frappe.qb.from_(Pin).select(Pin.project).where(Pin.user == frappe.session.user)
	projects = (
		frappe.qb.from_(ProjectVisit)
		.select(
			ProjectVisit.project.as_("name"),
			Project.team,
			Project.title.as_("project_title"),
			Team.title.as_("team_title"),
			Project.icon,
			Max(ProjectVisit.last_visit).as_("timestamp"),
		)
		.left_join(Project)
		.on(Project.name == ProjectVisit.project)
		.left_join(Team)
		.on(Team.name == Project.team)
		.groupby(ProjectVisit.project)
		.where(ProjectVisit.user == frappe.session.user)
		.where(ProjectVisit.project.notin(pinned_projects_query))
		.orderby(ProjectVisit.last_visit, order=frappe.qb.desc)
		.limit(12)
	)

	return projects.run(as_dict=1)


@frappe.whitelist()
def active_projects():
	from frappe.query_builder.functions import Count

	Comment = frappe.qb.DocType("GP Comment")
	Discussion = frappe.qb.DocType("GP Discussion")
	CommentCount = Count(Comment.name).as_("comments_count")
	active_projects = (
		frappe.qb.from_(Comment)
		.select(CommentCount, Discussion.project)
		.left_join(Discussion)
		.on(Discussion.name == Comment.reference_name)
		.where(Comment.reference_doctype == "GP Discussion")
		.where(Comment.creation > frappe.utils.add_days(frappe.utils.now(), -70))
		.groupby(Discussion.project)
		.orderby(CommentCount, order=frappe.qb.desc)
		.limit(12)
	).run(as_dict=1)

	projects = frappe.qb.get_query(
		"GP Project",
		fields=[
			"name",
			"title as project_title",
			"team",
			"team.title as team_title",
			"icon",
			"modified as timestamp",
		],
		filters={"name": ("in", [d.project for d in active_projects])},
	).run(as_dict=1)

	active_projects_comment_count = {d.project: d.comments_count for d in active_projects}
	for d in projects:
		d.comments_count = active_projects_comment_count.get(str(d.name), 0)

	projects.sort(key=lambda d: d.comments_count, reverse=True)

	return projects


@frappe.whitelist()
def onboarding(space, icon, emails):
	emails = frappe.parse_json(emails)
	project = frappe.get_doc(doctype="GP Project", title=space, icon=icon).insert()
	invite_by_email(", ".join(emails), role="Gameplan Member")
	return project.name


@frappe.whitelist(allow_guest=True)
def oauth_providers():
	from frappe.utils.html_utils import get_icon_html
	from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
	from frappe.utils.password import get_decrypted_password

	out = []
	providers = frappe.get_all(
		"Social Login Key",
		filters={"enable_social_login": 1},
		fields=["name", "client_id", "base_url", "provider_name", "icon"],
		order_by="name",
	)

	for provider in providers:
		client_secret = get_decrypted_password("Social Login Key", provider.name, "client_secret")
		if not client_secret:
			continue

		icon = None
		if provider.icon:
			if provider.provider_name == "Custom":
				icon = get_icon_html(provider.icon, small=True)
			else:
				icon = f"<img src='{provider.icon}' alt={provider.provider_name}>"

		if provider.client_id and provider.base_url and get_oauth_keys(provider.name):
			out.append(
				{
					"name": provider.name,
					"provider_name": provider.provider_name,
					"auth_url": get_oauth2_authorize_url(provider.name, "/g"),
					"icon": icon,
				}
			)
	return out


@frappe.whitelist()
def search_sqlite(query, filters=None):
	from gameplan.search_sqlite import GameplanSearch

	search = GameplanSearch()

	# Parse filters if provided as JSON string
	if filters and isinstance(filters, str):
		import json

		filters = json.loads(filters)

	result = search.search(query, filters=filters)
	return result


@frappe.whitelist()
def get_search_filter_options():
	"""Get available filter options for advanced search"""
	from gameplan.search_sqlite import GameplanSearch

	search = GameplanSearch()
	return search.get_filter_options()


def can_access_gameplan():
	"""Check if the app should be shown in /apps"""
	if frappe.session.user == "Administrator":
		return True

	from frappe.config import get_modules_from_all_apps_for_user

	allowed_modules = [x["module_name"] for x in get_modules_from_all_apps_for_user()]
	if "Gameplan" not in allowed_modules:
		return False

	roles = set(frappe.get_roles())
	allowed_roles = set(["System Manager", "Gameplan Admin", "Gameplan Member", "Gameplan Guest"])
	if roles.intersection(allowed_roles):
		return True

	return False


@frappe.whitelist()
def get_space_operations(space_id: str):
	"""Return the operating snapshot for a Gameplan space.

	The frontend intentionally consumes this instead of keeping product-ops
	assumptions in Vue. Until sprint/work-type fields become first-class
	doctype fields, those dimensions are derived from existing task data.
	"""
	if not space_id or not frappe.db.exists("GP Project", space_id):
		frappe.throw("Invalid space", frappe.DoesNotExistError)

	project = frappe.get_doc("GP Project", space_id)
	if not frappe.has_permission("GP Project", "read", doc=project):
		frappe.throw("Not permitted", frappe.PermissionError)

	tasks = _get_operation_tasks(space_id)
	discussions = _get_operation_discussions(space_id)
	pages = _get_operation_pages(space_id)

	return {
		"space": {
			"name": str(project.name),
			"title": project.title,
			"team": project.team,
			"team_title": frappe.db.get_value("GP Team", project.team, "title") if project.team else None,
			"is_private": project.is_private,
			"members_count": frappe.db.count("GP Member", {"parenttype": "GP Project", "parent": project.name}),
		},
		"metrics": _get_operation_metrics(tasks, discussions, pages),
		"work": _summarize_operation_tasks(tasks),
		"sprints": _summarize_sprint_buckets(tasks),
		"calendar": _summarize_calendar(tasks),
		"collections": _summarize_product_collections(project, tasks, discussions, pages),
		"intake": _summarize_intake(discussions),
		"decisions": _summarize_decisions(discussions, pages),
		"knowledge": _summarize_knowledge(pages),
		"rbac": _get_operation_rbac(project),
		"automation": _get_operation_automation_policy(),
	}


@frappe.whitelist()
def get_ai_handoff_context(reference_doctype: str, reference_name: str):
	"""Return read-only context for a human-authored OpenClaw handoff.

	This deliberately does not execute work or create downstream tasks. The
	payload is a small, versioned contract that UI and external agents can use
	to draft a visible comment that remains approval-gated in Gameplan.
	"""
	reference_doctype = (reference_doctype or "").strip()
	reference_name = (reference_name or "").strip()
	if reference_doctype not in ("GP Discussion", "GP Comment", "GP Task"):
		frappe.throw("AI handoff is available for discussions, comments, and tasks only")
	if not reference_name or not frappe.db.exists(reference_doctype, reference_name):
		frappe.throw("Invalid handoff reference", frappe.DoesNotExistError)

	reference = frappe.get_doc(reference_doctype, reference_name)
	if not frappe.has_permission(reference_doctype, "read", doc=reference):
		frappe.throw("Not permitted", frappe.PermissionError)

	discussion = _get_handoff_discussion(reference) if reference_doctype == "GP Comment" else None
	project_id = (
		discussion.project
		if discussion and discussion.project
		else reference.project
		if reference_doctype in ("GP Discussion", "GP Task") and reference.get("project")
		else None
	)
	project = _get_space_doc(project_id) if project_id else None
	feature_enabled = _is_openclaw_handoff_enabled()

	return {
		"schema": "gameplan.ai_handoff.v1",
		"assistant": {
			"name": "OpenClaw",
			"mention": "@OpenClaw",
			"mode": "human_visible_handoff",
		},
		"feature_flag": {
			"key": "gameplan_openclaw_handoff_enabled",
			"enabled": feature_enabled,
		},
		"reference": _handoff_reference_payload(reference),
		"discussion": _handoff_discussion_payload(discussion) if discussion else None,
		"task": _handoff_task_payload(reference) if reference_doctype == "GP Task" else None,
		"space": _space_payload(project) if project else None,
		"rbac": _get_operation_rbac(project) if project else _get_handoff_fallback_rbac(),
		"automation": {
			**_get_operation_automation_policy(),
			"requires_human_approval": True,
			"execution": "No code or data-changing action is executed from this handoff",
		},
		"capabilities": [
			"summarize_thread",
			"draft_development_handoff",
			"identify_open_questions",
			"suggest_next_comment",
			"architect_task",
			"plan_code_work",
			"generate_artifacts",
		]
		if feature_enabled
		else [],
	}


def _get_operation_tasks(space_id):
	rows = frappe.get_all(
		"GP Task",
		filters={"project": space_id},
		fields=[
			"name",
			"project",
			"title",
			"status",
			"priority",
			"sprint",
			"sprint.title as sprint_title",
			"assigned_to",
			"owner",
			"due_date",
			"creation",
			"modified",
			"comments_count",
		],
		order_by="due_date asc, `tabGP Task`.modified desc",
		limit=200,
	)
	for row in rows:
		row["work_type"] = _classify_work_type(row)
		row["sprint_bucket"] = _classify_sprint_bucket(row.get("due_date"))
	return rows


def _get_operation_discussions(space_id):
	return frappe.get_all(
		"GP Discussion",
		filters={"project": space_id},
		fields=[
			"name",
			"project",
			"title",
			"status",
			"work_type",
			"decision_status",
			"decision_owner",
			"converted_task",
			"closed_at",
			"owner",
			"last_post_at",
			"comments_count",
			"participants_count",
			"slug",
		],
		order_by="last_post_at desc",
		limit=50,
	)


def _get_operation_pages(space_id):
	return frappe.get_all(
		"GP Page",
		filters={"project": space_id},
		fields=["name", "title", "owner", "modified", "slug", "category", "category.title as category_title"],
		order_by="`tabGP Page`.modified desc",
		limit=50,
	)


def _get_operation_metrics(tasks, discussions, pages):
	open_tasks = [task for task in tasks if task.get("status") not in ("Done", "Canceled")]
	blockers = [
		task
		for task in open_tasks
		if task.get("priority") == "Urgent" or "block" in (task.get("title") or "").lower()
	]
	return {
		"open_work": len(open_tasks),
		"blocked": len(blockers),
		"due_this_sprint": len([task for task in open_tasks if task.get("sprint_bucket") == "Current"]),
		"unassigned": len([task for task in open_tasks if not task.get("assigned_to")]),
		"discussions": len(discussions),
		"knowledge": len(pages),
	}


def _summarize_operation_tasks(tasks):
	return [
		{
			"name": str(task.name),
			"title": task.title,
			"status": task.status or "Backlog",
			"priority": task.priority,
			"assigned_to": task.assigned_to or task.owner,
			"due_date": task.due_date,
			"work_type": task.work_type,
			"sprint_bucket": task.sprint_bucket,
			"sprint": task.sprint,
			"sprint_title": task.sprint_title,
			"comments_count": task.comments_count or 0,
		}
		for task in tasks
	]


def _summarize_sprint_buckets(tasks):
	buckets = {
		"Overdue": [],
		"Current": [],
		"Next": [],
		"Backlog": [],
		"Done": [],
	}
	for task in tasks:
		bucket = "Done" if task.get("status") in ("Done", "Canceled") else task.get("sprint_bucket")
		buckets.setdefault(bucket, []).append(task)

	return [
		{
			"name": name,
			"count": len(items),
			"blocked": len([task for task in items if task.get("priority") == "Urgent"]),
			"unassigned": len([task for task in items if not task.get("assigned_to")]),
		}
		for name, items in buckets.items()
		if items or name in ("Current", "Next", "Backlog")
	]


def _summarize_calendar(tasks):
	items = []
	for task in tasks:
		if not task.get("due_date") or task.get("status") in ("Done", "Canceled"):
			continue
		items.append(
			{
				"name": str(task.name),
				"title": task.title,
				"date": task.due_date,
				"status": task.status or "Backlog",
				"priority": task.priority,
				"owner": task.assigned_to or task.owner,
				"work_type": task.work_type,
				"sprint_bucket": task.sprint_bucket,
			}
		)
	return items[:12]


def _summarize_product_collections(project, tasks, discussions, pages):
	open_tasks = [task for task in tasks if task.get("status") not in ("Done", "Canceled")]
	current_tasks = [task for task in open_tasks if task.get("sprint_bucket") == "Current"]
	release_tasks = [task for task in open_tasks if task.get("work_type") == "Release"]
	decision_discussions = [
		discussion
		for discussion in discussions
		if discussion.get("work_type") == "Decision Needed"
		or discussion.get("decision_status")
		or any(word in (discussion.title or "").lower() for word in ("decision", "signoff", "approval", "policy"))
	]
	customer_discussions = [
		discussion
		for discussion in discussions
		if any(word in (discussion.title or "").lower() for word in ("customer", "uat", "poc", "ticket"))
	]

	collections = [
		{
			"name": "current-sprint",
			"title": "Current Sprint Pack",
			"purpose": "What the scrum master needs for this sprint",
			"tasks": len(current_tasks),
			"discussions": len(discussions),
			"pages": len(pages),
			"health": _collection_health(current_tasks),
		},
		{
			"name": "release-readiness",
			"title": "Release Readiness Pack",
			"purpose": "Deployments, checklists, blockers, signoffs",
			"tasks": len(release_tasks),
			"discussions": len([d for d in discussions if "release" in (d.title or "").lower()]),
			"pages": len([p for p in pages if any(w in (p.title or "").lower() for w in ("release", "deploy", "checklist"))]),
			"health": _collection_health(release_tasks),
		},
		{
			"name": "decisions",
			"title": "Decision Register",
			"purpose": "Approvals, assumptions, CTO/product choices",
			"tasks": len([task for task in open_tasks if task.get("work_type") == "Decision"]),
			"discussions": len(decision_discussions),
			"pages": len([p for p in pages if any(w in (p.title or "").lower() for w in ("decision", "model", "policy", "signoff"))]),
			"health": "Needs review" if decision_discussions else "Clear",
		},
		{
			"name": "customer-context",
			"title": "Customer / POC Pack",
			"purpose": "UAT, customer evidence, Helpdesk escalations",
			"tasks": len([task for task in open_tasks if task.get("work_type") in ("Bug", "Story")]),
			"discussions": len(customer_discussions),
			"pages": len([p for p in pages if any(w in (p.title or "").lower() for w in ("customer", "uat", "poc", "architecture"))]),
			"health": "Active" if customer_discussions or "poc" in (project.title or "").lower() else "Quiet",
		},
	]
	return collections


def _collection_health(tasks):
	if not tasks:
		return "Empty"
	if any(task.get("priority") == "Urgent" for task in tasks):
		return "Blocked"
	if any(not task.get("assigned_to") for task in tasks):
		return "Needs owner"
	return "On track"


def _summarize_intake(discussions):
	out = []
	for discussion in discussions[:8]:
		out.append(
			{
				"name": str(discussion.name),
				"title": discussion.title,
				"source": "Discussion",
				"status": "Closed" if discussion.closed_at else "Open",
				"owner": discussion.owner,
				"last_post_at": discussion.last_post_at,
				"comments_count": discussion.comments_count or 0,
				"slug": discussion.slug,
			}
		)
	return out


def _summarize_decisions(discussions, pages):
	decision_words = ("decision", "signoff", "approval", "policy", "model", "assumption")
	candidates = []
	for discussion in discussions:
		title = (discussion.title or "").lower()
		if (
			discussion.get("work_type") == "Decision Needed"
			or discussion.get("decision_status")
			or any(word in title for word in decision_words)
		):
			candidates.append(
				{
					"type": "Discussion",
					"name": str(discussion.name),
					"title": discussion.title,
					"owner": discussion.owner,
					"status": "Closed" if discussion.closed_at else "Open",
					"decision_status": discussion.decision_status,
					"updated_at": discussion.last_post_at,
					"slug": discussion.slug,
				}
			)
	for page in pages:
		title = (page.title or "").lower()
		if any(word in title for word in decision_words):
			candidates.append(
				{
					"type": "Page",
					"name": str(page.name),
					"title": page.title,
					"owner": page.owner,
					"status": "Documented",
					"updated_at": page.modified,
					"slug": page.slug,
				}
			)
	return candidates[:6]


@frappe.whitelist()
def get_space_sdlc(space_id: str):
	project = _get_space_doc(space_id)
	return {
		"space": _space_payload(project),
		"sprints": get_space_sprints(space_id),
		"calendar": get_space_calendar(space_id),
		"decisions": get_space_decisions(space_id),
		"knowledge": get_space_knowledge(space_id),
	}


@frappe.whitelist()
def get_space_sprints(space_id: str):
	_get_space_doc(space_id)
	sprints = frappe.get_all(
		"GP Sprint",
		filters={"project": space_id},
		fields=["name", "title", "status", "start_date", "end_date", "goal", "sprint_owner"],
		order_by="start_date asc, creation asc",
	)
	tasks = frappe.get_all(
		"GP Task",
		filters={"project": space_id},
		fields=[
			"name",
			"project",
			"title",
			"status",
			"priority",
			"sprint",
			"sprint.title as sprint_title",
			"assigned_to",
			"owner",
			"due_date",
			"testing_notes",
			"proof_url",
			"source_type",
			"source_doctype",
			"source_name",
		],
		order_by="due_date asc, `tabGP Task`.modified desc",
		limit=300,
	)
	for sprint in sprints:
		sprint["name"] = str(sprint.name)
		sprint["tasks"] = [task for task in tasks if str(task.get("sprint") or "") == sprint.name]
		sprint["open_tasks"] = len([task for task in sprint["tasks"] if task.get("status") not in ("Done", "Canceled")])
		sprint["blocked_tasks"] = len([task for task in sprint["tasks"] if task.get("priority") == "Urgent"])
	backlog = [task for task in tasks if not task.get("sprint")]
	return {
		"sprints": sprints,
		"backlog": backlog,
	}


@frappe.whitelist()
def get_all_sprints():
	rows = []
	for project in _get_accessible_spaces():
		data = get_space_sprints(str(project.name))
		for sprint in data["sprints"]:
			sprint["space"] = str(project.name)
			sprint["space_title"] = project.title
			rows.append(sprint)
	return rows


@frappe.whitelist()
def get_kanban_tasks(space_id=None):
	projects = [_get_space_doc(space_id)] if space_id else _get_accessible_spaces()
	project_titles = {str(project.name): project.title for project in projects}
	tasks = []
	for project in projects:
		tasks.extend(
			frappe.get_all(
				"GP Task",
				filters={"project": project.name, "status": ["not in", ["Canceled"]]},
				fields=[
					"name",
					"project",
					"title",
					"status",
					"priority",
					"assigned_to",
					"owner",
					"due_date",
					"sprint",
					"sprint.title as sprint_title",
					"source_type",
					"source_doctype",
					"source_name",
					"testing_notes",
					"proof_url",
					"comments_count",
				],
				order_by="`tabGP Task`.modified desc",
				limit=300,
			)
		)
	for task in tasks:
		task["space"] = str(task.project)
		task["space_title"] = project_titles.get(str(task.project), str(task.project))
		task["lane"] = _kanban_lane(task.status)
	return tasks


@frappe.whitelist()
def get_space_calendar(space_id: str):
	_get_space_doc(space_id)
	events = []
	for sprint in frappe.get_all(
		"GP Sprint",
		filters={"project": space_id},
		fields=["name", "title", "status", "start_date", "end_date"],
		order_by="start_date asc",
	):
		if sprint.start_date:
			events.append({"type": "Sprint Start", "date": sprint.start_date, "title": sprint.title, "status": sprint.status, "name": sprint.name})
		if sprint.end_date:
			events.append({"type": "Sprint End", "date": sprint.end_date, "title": sprint.title, "status": sprint.status, "name": sprint.name})
	for task in frappe.get_all(
		"GP Task",
		filters={"project": space_id, "due_date": ["is", "set"]},
		fields=["name", "title", "status", "priority", "due_date", "assigned_to", "sprint", "sprint.title as sprint_title"],
		order_by="due_date asc",
		limit=200,
	):
		events.append(
			{
				"type": "Task Due",
				"date": task.due_date,
				"title": task.title,
				"status": task.status,
				"priority": task.priority,
				"owner": task.assigned_to,
				"name": task.name,
				"sprint": task.sprint,
				"sprint_title": task.sprint_title,
			}
		)
	return sorted(events, key=lambda event: event.get("date") or "")


@frappe.whitelist()
def get_all_calendar():
	events = []
	for project in _get_accessible_spaces():
		for event in get_space_calendar(str(project.name)):
			event["space"] = str(project.name)
			event["space_title"] = project.title
			events.append(event)
	return sorted(events, key=lambda event: event.get("date") or "")


@frappe.whitelist()
def get_space_decisions(space_id: str):
	_get_space_doc(space_id)
	discussions = frappe.get_all(
		"GP Discussion",
		filters={"project": space_id},
		fields=[
			"name",
			"project",
			"title",
			"slug",
			"status",
			"work_type",
			"decision_status",
			"decision_owner",
			"approved_by",
			"approved_at",
			"converted_task",
			"owner",
			"last_post_at",
			"comments_count",
			"closed_at",
		],
		order_by="last_post_at desc",
		limit=200,
	)
	decision_words = ("decision", "signoff", "approval", "policy", "model", "assumption")
	return [
		discussion
		for discussion in discussions
		if discussion.get("work_type") == "Decision Needed"
		or discussion.get("decision_status")
		or any(word in (discussion.get("title") or "").lower() for word in decision_words)
	]


@frappe.whitelist()
def get_all_decisions():
	decisions = []
	for project in _get_accessible_spaces():
		for decision in get_space_decisions(str(project.name)):
			decision["space"] = str(project.name)
			decision["space_title"] = project.title
			decisions.append(decision)
	return decisions


@frappe.whitelist()
def get_space_knowledge(space_id: str):
	_get_space_doc(space_id)
	categories = frappe.get_all(
		"GP Page Category",
		filters={"project": space_id},
		fields=["name", "title", "description", "icon", "idx"],
		order_by="idx asc, title asc",
	)
	pages = frappe.get_all(
		"GP Page",
		filters={"project": space_id},
		fields=["name", "title", "slug", "category", "category.title as category_title", "owner", "modified"],
		order_by="`tabGP Page`.modified desc",
		limit=300,
	)
	for category in categories:
		category["name"] = str(category.name)
		category["pages"] = [page for page in pages if str(page.get("category") or "") == category.name]
	uncategorized = [page for page in pages if not page.get("category")]
	return {"categories": categories, "uncategorized": uncategorized}


@frappe.whitelist()
def create_space_sprint(space_id: str, title: str, status: str = "Planned", start_date=None, end_date=None, goal=None):
	_get_space_doc(space_id)
	doc = frappe.get_doc(
		{
			"doctype": "GP Sprint",
			"project": space_id,
			"title": title,
			"status": status or "Planned",
			"start_date": start_date,
			"end_date": end_date,
			"goal": goal,
			"sprint_owner": frappe.session.user,
		}
	)
	doc.insert()
	return doc.as_dict()


@frappe.whitelist()
def create_page_category(space_id: str, title: str, description=None, icon=None):
	_get_space_doc(space_id)
	doc = frappe.get_doc(
		{
			"doctype": "GP Page Category",
			"project": space_id,
			"title": title,
			"description": description,
			"icon": icon,
		}
	)
	doc.insert()
	return doc.as_dict()


@frappe.whitelist()
def mark_discussion_for_decision(discussion_id: str, decision_status: str = "Needs Approval", decision_owner=None):
	doc = frappe.get_doc("GP Discussion", discussion_id)
	if not frappe.has_permission("GP Discussion", "write", doc=doc):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc.work_type = "Decision Needed"
	doc.decision_status = decision_status or "Needs Approval"
	doc.decision_owner = decision_owner or frappe.session.user
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def approve_discussion_decision(discussion_id: str):
	doc = frappe.get_doc("GP Discussion", discussion_id)
	if not frappe.has_permission("GP Discussion", "write", doc=doc):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc.work_type = "Decision Needed"
	doc.decision_status = "Approved"
	doc.approved_by = frappe.session.user
	doc.approved_at = frappe.utils.now()
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def convert_discussion_to_task(discussion_id: str, sprint=None, assigned_to=None, priority="Medium"):
	discussion = frappe.get_doc("GP Discussion", discussion_id)
	if not frappe.has_permission("GP Discussion", "write", doc=discussion):
		frappe.throw("Not permitted", frappe.PermissionError)
	if sprint and frappe.db.get_value("GP Sprint", sprint, "project") != discussion.project:
		frappe.throw("Sprint does not belong to this space")

	task = frappe.get_doc(
		{
			"doctype": "GP Task",
			"project": discussion.project,
			"title": discussion.title,
			"description": discussion.content,
			"status": "Todo" if sprint else "Backlog",
			"priority": priority or "Medium",
			"sprint": sprint,
			"assigned_to": assigned_to or discussion.decision_owner or frappe.session.user,
			"source_type": "Discussion",
			"source_doctype": "GP Discussion",
			"source_name": discussion.name,
		}
	)
	task.insert()
	discussion.work_type = "Decision Needed"
	discussion.decision_status = "Converted to Task"
	discussion.converted_task = task.name
	discussion.save()
	return task.as_dict()


@frappe.whitelist()
def assign_task_to_sprint(task_id: str, sprint=None):
	task = frappe.get_doc("GP Task", task_id)
	if not frappe.has_permission("GP Task", "write", doc=task):
		frappe.throw("Not permitted", frappe.PermissionError)
	if sprint and frappe.db.get_value("GP Sprint", sprint, "project") != task.project:
		frappe.throw("Sprint does not belong to this task's space")
	task.sprint = sprint
	if sprint and task.status == "Backlog":
		task.status = "Todo"
	task.save()
	return task.as_dict()


@frappe.whitelist()
def update_task_planning(task_id: str, sprint=None, assigned_to=None, status=None):
	task = frappe.get_doc("GP Task", task_id)
	if not frappe.has_permission("GP Task", "write", doc=task):
		frappe.throw("Not permitted", frappe.PermissionError)
	if sprint is not None:
		sprint = sprint or None
		if sprint and frappe.db.get_value("GP Sprint", sprint, "project") != task.project:
			frappe.throw("Sprint does not belong to this task's space")
		task.sprint = sprint
	if assigned_to is not None:
		task.assigned_to = assigned_to or None
	if status:
		task.status = status
	elif sprint and task.status == "Backlog":
		task.status = "Todo"
	task.save()
	return task.as_dict()


@frappe.whitelist()
def seed_space_sdlc(space_id: str):
	_get_space_doc(space_id)
	today = frappe.utils.getdate(frappe.utils.nowdate())
	if not frappe.db.exists("GP Sprint", {"project": space_id, "status": "Current"}):
		create_space_sprint(
			space_id=space_id,
			title="Current Sprint",
			status="Current",
			start_date=today,
			end_date=frappe.utils.add_days(today, 14),
			goal="Active delivery work for this space",
		)
	if not frappe.db.exists("GP Sprint", {"project": space_id, "status": "Planned"}):
		create_space_sprint(
			space_id=space_id,
			title="Next Sprint",
			status="Planned",
			start_date=frappe.utils.add_days(today, 15),
			end_date=frappe.utils.add_days(today, 28),
			goal="Upcoming work after current commitments",
		)
	current_sprint = frappe.db.get_value(
		"GP Sprint", {"project": space_id, "status": "Current"}, ["name", "end_date"], as_dict=True
	)
	if current_sprint:
		for task in frappe.get_all(
			"GP Task",
			filters={
				"project": space_id,
				"sprint": ["is", "not set"],
				"status": ["not in", ["Done", "Canceled"]],
				"due_date": ["<=", current_sprint.end_date],
			},
			pluck="name",
		):
			frappe.db.set_value("GP Task", task, "sprint", current_sprint.name, update_modified=False)
	for idx, title in enumerate(["Architecture", "Configs and Runbooks", "Testing Evidence", "Release Notes", "Customer Context"], start=1):
		if not frappe.db.exists("GP Page Category", {"project": space_id, "title": title}):
			doc = frappe.get_doc(
				{
					"doctype": "GP Page Category",
					"project": space_id,
					"title": title,
					"description": f"{title} pages for this space",
					"idx": idx,
				}
			)
			doc.insert()
	return get_space_sdlc(space_id)


@frappe.whitelist()
def seed_cto_demo_discussions(space_id: str):
	"""Create realistic product-ops decision discussions for a CTO demo."""
	project = _get_space_doc(space_id)
	users = _ensure_demo_users()
	_ensure_space_members(project, users)

	templates = [
		{
			"title": "Decision: approve OpenClaw OAuth federation model",
			"owner": "cto@gameplan.local",
			"status": "Needs Approval",
			"content": """
				<h2>Decision needed</h2>
				<p>We need to finalize whether OpenClaw should federate through NextAI OAuth into one Frappe user session or remain isolated per service profile.</p>
				<ul>
					<li><strong>Preferred option:</strong> NextAI owns OAuth handshake; OpenClaw gets scoped service context.</li>
					<li><strong>Risk:</strong> assistant execution must stay approval-gated for customer-impacting actions.</li>
					<li><strong>Required outcome:</strong> approved integration model before CTO demo workspace setup.</li>
				</ul>
			""",
			"comments": [
				("scrum.master@gameplan.local", "<p>From delivery planning, this should become a story only after the approval rule is agreed. Otherwise it will keep bouncing between sprint and backlog.</p>"),
				("ops.manager@gameplan.local", "<p>Ops needs the config boundary documented: profile name, vector DB collection, allowed Helpdesk actions, and rollback steps.</p>"),
				("codex.assistant@gameplan.local", "<p>I can draft the integration checklist after approval and attach the config file references as task proof.</p>"),
			],
		},
		{
			"title": "Signoff: Redis UAT tracker import and ownership rules",
			"owner": "scrum.master@gameplan.local",
			"status": "Approved",
			"content": """
				<h2>Context</h2>
				<p>The Redis UAT tracker spreadsheet is now represented as Gameplan work items. We need agreement on ownership and sprint movement rules.</p>
				<p><strong>Proposal:</strong> support-sourced issues land in backlog, scrum master triages, senior owner can assign directly, and sprint movement is visible on the sprint page.</p>
			""",
			"comments": [
				("cto@gameplan.local", "<p>Approved with one condition: L2/L3 support escalations should carry the Helpdesk ticket reference into the task.</p>"),
				("qa.lead@gameplan.local", "<p>Testing proof needs a required attachment or URL before release readiness is marked complete.</p>"),
			],
		},
		{
			"title": "Architecture choice: Drive-linked release evidence pack",
			"owner": "ops.manager@gameplan.local",
			"status": "Needs Approval",
			"content": """
				<h2>Choice</h2>
				<p>Release evidence should be grouped as a knowledge pack, not scattered across individual pages.</p>
				<ul>
					<li>Drive links hold source files: spreadsheets, presentations, YAML/configs.</li>
					<li>Pages summarize release notes, testing evidence, and customer context.</li>
					<li>Tasks link back to the evidence pack before final testing.</li>
				</ul>
			""",
			"comments": [
				("qa.lead@gameplan.local", "<p>This solves the UAT handoff problem. I need one place to see test proof, blocking defects, and final signoff.</p>"),
				("scrum.master@gameplan.local", "<p>We should keep release packs separate from sprint boards so planning stays readable.</p>"),
			],
		},
		{
			"title": "Policy: AI assistant can classify intake but cannot execute without approval",
			"owner": "codex.assistant@gameplan.local",
			"status": "Converted to Task",
			"content": """
				<h2>Guardrail</h2>
				<p>Assistant work should be visible in Gameplan as suggestions first. Execution requires a human approval record.</p>
				<p>This applies to Codex task creation, Helpdesk L2/L3 intake, config updates, and OpenClaw profile changes.</p>
			""",
			"comments": [
				("cto@gameplan.local", "<p>This is the right default. We can loosen this only after audit logs and rollback are proven.</p>"),
				("ops.manager@gameplan.local", "<p>Converted to task for implementation in the current sprint.</p>"),
			],
		},
	]

	current_sprint = frappe.db.get_value("GP Sprint", {"project": space_id, "status": "Current"}, "name")
	created = []
	previous_user = frappe.session.user
	try:
		for template in templates:
			discussion = _upsert_demo_decision(project.name, template, users)
			if template["status"] == "Converted to Task" and not discussion.converted_task:
				task = convert_discussion_to_task(discussion.name, sprint=current_sprint, assigned_to="ops.manager@gameplan.local")
				discussion = frappe.get_doc("GP Discussion", discussion.name)
				discussion.converted_task = task.name
			created.append(discussion.name)
	finally:
		frappe.set_user(previous_user)

	frappe.get_doc("GP Project", project.name).update_discussions_count()
	frappe.db.commit()
	return {"created": created, "decisions": get_space_decisions(space_id)}


def _ensure_demo_users():
	demo_users = [
		{"email": "cto@gameplan.local", "first_name": "Aarav", "last_name": "CTO", "role": "Gameplan Admin"},
		{"email": "scrum.master@gameplan.local", "first_name": "Meera", "last_name": "Scrum Master", "role": "Gameplan Member"},
		{"email": "ops.manager@gameplan.local", "first_name": "Kabir", "last_name": "Ops Manager", "role": "Gameplan Member"},
		{"email": "qa.lead@gameplan.local", "first_name": "Naina", "last_name": "QA Lead", "role": "Gameplan Member"},
		{"email": "codex.assistant@gameplan.local", "first_name": "Codex", "last_name": "Assistant", "role": "Gameplan Member"},
	]
	for user in demo_users:
		if not frappe.db.exists("User", user["email"]):
			doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": user["email"],
					"first_name": user["first_name"],
					"last_name": user["last_name"],
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
				}
			)
			doc.insert(ignore_permissions=True)
		user_doc = frappe.get_doc("User", user["email"])
		roles = {role.role for role in user_doc.roles}
		for role in {user["role"], "Gameplan Member"} - roles:
			user_doc.append("roles", {"role": role})
		user_doc.enabled = 1
		user_doc.save(ignore_permissions=True)
	return [user["email"] for user in demo_users]


def _ensure_space_members(project, users):
	existing = {member.user for member in project.members}
	for user in users:
		if user not in existing:
			project.append("members", {"user": user})
	project.save(ignore_permissions=True)


def _upsert_demo_decision(project_name, template, users):
	existing = frappe.db.get_value("GP Discussion", {"project": project_name, "title": template["title"]}, "name")
	previous_user = frappe.session.user
	frappe.set_user(template["owner"])
	if existing:
		discussion = frappe.get_doc("GP Discussion", existing)
		discussion.content = template["content"]
	else:
		discussion = frappe.get_doc(
			{
				"doctype": "GP Discussion",
				"project": project_name,
				"title": template["title"],
				"content": template["content"],
				"work_type": "Decision Needed",
				"decision_owner": template["owner"],
			}
		)
	discussion.work_type = "Decision Needed"
	discussion.decision_status = template["status"]
	discussion.decision_owner = template["owner"]
	discussion.save(ignore_permissions=True) if existing else discussion.insert(ignore_permissions=True)
	discussion = frappe.get_doc("GP Discussion", discussion.name)
	frappe.set_user(previous_user)

	for owner, content in template["comments"]:
		if frappe.db.exists(
			"GP Comment",
			{
				"reference_doctype": "GP Discussion",
				"reference_name": discussion.name,
				"owner": owner,
				"content": content,
			},
		):
			continue
		current_user = frappe.session.user
		frappe.set_user(owner)
		comment = frappe.get_doc(
			{
				"doctype": "GP Comment",
				"reference_doctype": "GP Discussion",
				"reference_name": discussion.name,
				"content": content,
			}
		)
		comment.insert(ignore_permissions=True)
		frappe.set_user(current_user)

	discussion.reload()
	return discussion


def _get_space_doc(space_id):
	if not space_id or not frappe.db.exists("GP Project", space_id):
		frappe.throw("Invalid space", frappe.DoesNotExistError)
	project = frappe.get_doc("GP Project", space_id)
	if not frappe.has_permission("GP Project", "read", doc=project):
		frappe.throw("Not permitted", frappe.PermissionError)
	return project


def _get_accessible_spaces():
	projects = frappe.get_all(
		"GP Project",
		filters={"archived_at": ["is", "not set"]},
		fields=["name", "title", "team"],
		order_by="modified desc",
		limit=500,
	)
	return [
		project
		for project in projects
		if frappe.has_permission("GP Project", "read", doc=frappe.get_doc("GP Project", project.name))
	]


def _space_payload(project):
	return {
		"name": str(project.name),
		"title": project.title,
		"team": project.team,
		"team_title": frappe.db.get_value("GP Team", project.team, "title") if project.team else None,
	}


def _summarize_knowledge(pages):
	return [
		{
			"type": "Page",
			"name": str(page.name),
			"title": page.title,
			"owner": page.owner,
			"updated_at": page.modified,
			"slug": page.slug,
			"category": page.category,
			"category_title": page.category_title or "Uncategorized",
		}
		for page in pages[:8]
	]


def _get_operation_rbac(project):
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	space_member = bool(
		frappe.db.exists("GP Member", {"parenttype": "GP Project", "parent": project.name, "user": user})
	)
	is_guest = gameplan.is_guest(user)
	can_manage = "System Manager" in roles or "Gameplan Admin" in roles
	can_execute_ai = can_manage or "Gameplan Member" in roles

	return {
		"user": user,
		"roles": sorted([role for role in roles if role.startswith("Gameplan") or role == "System Manager"]),
		"space_member": space_member,
		"can_read": frappe.has_permission("GP Project", "read", doc=project),
		"can_create_task": frappe.has_permission("GP Task", "create"),
		"can_write_task": frappe.has_permission("GP Task", "write"),
		"can_create_discussion": frappe.has_permission("GP Discussion", "create"),
		"can_manage_space": can_manage,
		"can_execute_ai": can_execute_ai and not is_guest,
	}


def _get_operation_automation_policy():
	roles = set(frappe.get_roles())
	can_execute = bool({"System Manager", "Gameplan Admin", "Gameplan Member"} & roles)
	return {
		"identity": frappe.session.user,
		"requires_human_approval": True,
		"codex_execution": "Allowed after approval" if can_execute else "Read-only suggestions",
		"nextai": "Can draft and classify; cannot execute without approval",
	}


def _is_openclaw_handoff_enabled():
	return frappe.conf.get("gameplan_openclaw_handoff_enabled", True) not in (False, 0, "0", "false", "False")


def _get_handoff_discussion(comment):
	if comment.reference_doctype != "GP Discussion" or not comment.reference_name:
		frappe.throw("AI handoff comments must belong to a discussion")
	discussion = frappe.get_doc("GP Discussion", comment.reference_name)
	if not frappe.has_permission("GP Discussion", "read", doc=discussion):
		frappe.throw("Not permitted", frappe.PermissionError)
	return discussion


def _handoff_reference_payload(doc):
	payload = {
		"doctype": doc.doctype,
		"name": str(doc.name),
		"owner": doc.owner,
		"created_at": doc.creation,
		"modified": doc.modified,
	}
	if doc.doctype == "GP Discussion":
		payload.update(
			{
				"title": doc.title,
				"slug": doc.slug,
				"work_type": doc.work_type,
				"decision_status": doc.decision_status,
				"excerpt": _handoff_excerpt(doc.content),
			}
		)
	elif doc.doctype == "GP Comment":
		payload.update(
			{
				"reference_doctype": doc.reference_doctype,
				"reference_name": str(doc.reference_name),
				"excerpt": _handoff_excerpt(doc.content),
			}
		)
	elif doc.doctype == "GP Task":
		payload.update(_handoff_task_payload(doc))
	return payload


def _handoff_discussion_payload(discussion):
	return {
		"doctype": "GP Discussion",
		"name": str(discussion.name),
		"title": discussion.title,
		"slug": discussion.slug,
		"owner": discussion.owner,
		"work_type": discussion.work_type,
		"decision_status": discussion.decision_status,
		"comments_count": discussion.comments_count,
	}


def _handoff_task_payload(task):
	return {
		"doctype": "GP Task",
		"name": str(task.name),
		"title": task.title,
		"owner": task.owner,
		"status": task.status,
		"priority": task.priority,
		"assigned_to": task.assigned_to,
		"project": str(task.project) if task.project else None,
		"sprint": str(task.sprint) if task.sprint else None,
		"due_date": task.due_date,
		"comments_count": task.comments_count,
		"work_type": _classify_work_type(task.as_dict()),
		"description_excerpt": _handoff_excerpt(task.description),
	}


def _handoff_excerpt(content, limit=240):
	text = " ".join(strip_html(content or "").split())
	if len(text) <= limit:
		return text
	return f"{text[: limit - 3].rstrip()}..."


def _get_handoff_fallback_rbac():
	roles = set(frappe.get_roles())
	is_guest = gameplan.is_guest(frappe.session.user)
	return {
		"user": frappe.session.user,
		"roles": sorted([role for role in roles if role.startswith("Gameplan") or role == "System Manager"]),
		"can_read": True,
		"can_execute_ai": bool({"System Manager", "Gameplan Admin", "Gameplan Member"} & roles) and not is_guest,
	}


def _classify_work_type(task):
	text = f"{task.get('title') or ''} {task.get('description') or ''}".lower()
	if any(word in text for word in ("bug", "fail", "error", "broken", "fix")):
		return "Bug"
	if any(word in text for word in ("decision", "signoff", "approval", "assumption", "policy")):
		return "Decision"
	if any(word in text for word in ("release", "deploy", "checklist", "migration")):
		return "Release"
	if any(word in text for word in ("story", "design", "define", "prepare", "create", "implement", "add")):
		return "Story"
	return "Task"


def _classify_sprint_bucket(due_date):
	if not due_date:
		return "Backlog"
	today = frappe.utils.getdate(frappe.utils.nowdate())
	due = frappe.utils.getdate(due_date)
	if due < today:
		return "Overdue"
	if due <= frappe.utils.add_days(today, 14):
		return "Current"
	if due <= frappe.utils.add_days(today, 28):
		return "Next"
	return "Backlog"


def _kanban_lane(status):
	if status in ("Done",):
		return "Done"
	if status in ("In Progress",):
		return "In Progress"
	if status in ("Todo",):
		return "Todo"
	return "Backlog"
