from .logger import log
from .attiodata import AttioData
from .fixdata import FixData
from .fixresources import FixUser, FixWorkspace
from .attioresources import AttioUser, AttioWorkspace


def sync_fix_to_attio(fix: FixData, attio: AttioData) -> None:
    workspaces_missing = workspaces_missing_in_attio(fix, attio)
    users_missing = users_missing_in_attio(fix, attio)
    obsolete_workspaces = workspaces_no_longer_in_fix(fix, attio)
    obsolete_users = users_no_longer_in_fix(fix, attio)
    users_outdated = users_outdated_in_attio(fix, attio)
    workspaces_outdated = workspaces_outdated_in_attio(fix, attio)

    for fix_workspace in workspaces_missing:
        log.info(f"Creating workspace {fix_workspace.name}")
        try:
            attio.assert_record(**fix_workspace.attio_data())
        except Exception as e:
            log.error(f"Error creating workspace {fix_workspace.name}: {e}")

    for fix_workspace in workspaces_outdated:
        log.info(f"Updating workspace {fix_workspace.name}")
        try:
            attio.assert_record(**fix_workspace.attio_data())
        except Exception as e:
            log.error(f"Error updating workspace {fix_workspace.name}: {e}")

    for user in users_missing:
        log.info(f"Asserting person {user.email}")
        try:
            attio_person = attio.assert_record(**user.attio_person())
            workspace_ids = [workspace.id for workspace in user.workspaces]
            attio_workspaces = [
                attio_workspace
                for attio_workspace in attio.workspaces
                if attio_workspace.fix_workspace_id in workspace_ids
            ]
            try:
                attio_user = attio.assert_record(**user.attio_data(attio_person, attio_workspaces))
                attio_user.person = attio_person
                attio_person.users.append(attio_user)
                attio_user.workspaces.extend(attio_workspaces)
                for attio_workspace in attio_workspaces:
                    attio_workspace.users.append(attio_user)
            except Exception as e:
                log.error(f"Error asserting user {user.email}: {e}")
        except Exception as e:
            log.error(f"Error asserting person {user.email}: {e}")

    for user in users_outdated:
        attio_user = None
        for au in attio.users:
            if au.id == user.id:
                attio_user = au
                break
        if attio_user is None:
            log.error(f"User {user.email} ({user.id}) not found in Attio - skipping")
            continue
        log.info(f"Updating user {user.email}")
        attio_person = attio_user.person
        workspace_ids = [workspace.id for workspace in user.workspaces]
        attio_workspaces = [
            attio_workspace for attio_workspace in attio.workspaces if attio_workspace.fix_workspace_id in workspace_ids
        ]
        try:
            attio_user = attio.assert_record(**user.attio_data(attio_person, attio_workspaces))
        except Exception as e:
            log.error(f"Error updating user {user.email}: {e}")


def workspaces_missing_in_attio(fix: FixData, attio: AttioData) -> list[FixWorkspace]:
    fix_workspace_ids = {workspace.id for workspace in fix.workspaces}
    attio_workspace_ids = {workspace.id for workspace in attio.workspaces}

    missing = fix_workspace_ids - attio_workspace_ids

    log.debug(f"Number of workspaces missing in Attio: {len(missing)}")

    return [fix_workspace for fix_workspace in fix.workspaces if fix_workspace.id in missing]


def users_missing_in_attio(fix: FixData, attio: AttioData) -> list[FixUser]:
    fix_user_ids = {user.id for user in fix.users}
    attio_user_ids = {user.id for user in attio.users}

    missing = fix_user_ids - attio_user_ids

    log.debug(f"Number of users missing in Attio: {len(missing)}")

    return [fix_user for fix_user in fix.users if fix_user.id in missing]


def users_no_longer_in_fix(fix: FixData, attio: AttioData) -> list[AttioUser]:
    fix_user_ids = {user.id for user in fix.users}
    attio_user_ids = {user.id for user in attio.users}

    missing = attio_user_ids - fix_user_ids

    log.debug(f"Number of users no longer in Fix: {len(missing)}")

    return [attio_user for attio_user in attio.users if attio_user.id in missing]


def workspaces_no_longer_in_fix(fix: FixData, attio: AttioData) -> list[AttioWorkspace]:
    fix_workspace_ids = {workspace.id for workspace in fix.workspaces}
    attio_workspace_ids = {workspace.id for workspace in attio.workspaces}

    missing = attio_workspace_ids - fix_workspace_ids

    log.debug(f"Number of workspaces no longer in Fix: {len(missing)}")

    return [attio_workspace for attio_workspace in attio.workspaces if attio_workspace.id in missing]


def users_outdated_in_attio(fix: FixData, attio: AttioData) -> list[FixUser]:
    fix_user_ids = {user.id for user in fix.users}
    attio_user_ids = {user.id for user in attio.users}

    common_user_ids = fix_user_ids & attio_user_ids

    fix_users_by_id = {user.id: user for user in fix.users}
    attio_users_by_id = {user.id: user for user in attio.users}

    outdated = set()

    for user_id in common_user_ids:
        fix_user = fix_users_by_id[user_id]
        attio_user = attio_users_by_id[user_id]

        if fix_user != attio_user:
            outdated.add(user_id)

    log.debug(f"Number of outdated users in Attio: {len(outdated)}")

    return [fix_user for fix_user in fix.users if fix_user.id in outdated]


def workspaces_outdated_in_attio(fix: FixData, attio: AttioData) -> list[FixWorkspace]:
    fix_workspace_ids = {workspace.id for workspace in fix.workspaces}
    attio_workspace_ids = {workspace.id for workspace in attio.workspaces}

    common_workspace_ids = fix_workspace_ids & attio_workspace_ids

    fix_workspaces_by_id = {workspace.id: workspace for workspace in fix.workspaces}
    attio_workspaces_by_id = {workspace.id: workspace for workspace in attio.workspaces}

    outdated = set()

    for workspace_id in common_workspace_ids:
        fix_workspace = fix_workspaces_by_id[workspace_id]
        attio_workspace = attio_workspaces_by_id[workspace_id]

        if fix_workspace != attio_workspace:
            outdated.add(workspace_id)

    log.debug(f"Number of outdated workspaces in Attio: {len(outdated)}")

    return [fix_workspace for fix_workspace in fix.workspaces if fix_workspace.id in outdated]
