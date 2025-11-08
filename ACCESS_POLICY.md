# Internal Access and API Policy

## Purpose
To protect and manage access to sensitive services and components in the OASYS platform.

## Modules Covered
- Internal Engines
- Validators
- Template Extraction Services
- User Data Management APIs
- Log Services

## Access Rules
- Do **not** expose internal APIs or microservices to external users
- All access must be authenticated and logged
- Admin access is granted through Django Admin only
- External access requires a signed NDA and explicit approval

## Forbidden Actions
- Public exposure of `templator`, `log_service`, or any engine endpoints
- Reverse engineering or re-use of microservice logic externally
- Redistribution of downloaded templates or internal data

## Allowed Use
Only under:
- Internal testing and development
- Admin-operated environments
- Explicit written permission from the creator