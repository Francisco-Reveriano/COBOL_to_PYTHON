"""GenApp insurance domain — port of ``cics-genapp/base/src/``.

Per SDD §7.2 and §8, the insurance domain lives in its own subpackage and
exposes a single FastAPI router (``app.insurance.router.router``) that the
top-level application includes alongside the existing CBSA banking surface.

The COBOL programs that this package replaces (per SDD §7.2):

* ``LGACUS01`` / ``LGACDB01`` / ``LGACVS01`` → :func:`app.insurance.services.add_customer`
* ``LGICUS01`` / ``LGICDB01`` / ``LGICVS01`` → :func:`app.insurance.services.inquire_customer`
* ``LGUCUS01`` / ``LGUCDB01`` / ``LGUCVS01`` → :func:`app.insurance.services.update_customer`
* ``LGAPOL01`` / ``LGAPDB01`` / ``LGAPVS01`` → :func:`app.insurance.services.add_policy`
* ``LGIPOL01`` / ``LGIPDB01`` / ``LGIPVS01`` → :func:`app.insurance.services.inquire_policy`
* ``LGUPOL01`` / ``LGUPDB01`` / ``LGUPVS01`` → :func:`app.insurance.services.update_policy`
* ``LGDPOL01`` / ``LGDPDB01`` / ``LGDPVS01`` → :func:`app.insurance.services.delete_policy`
* ``LGASTAT1``                                → :func:`app.insurance.services.increment_stat`
                                                   and :func:`app.insurance.services.get_stats`
* ``LGSETUP``                                 → :func:`app.insurance.services.setup_counters`
* ``LGSTSQ``                                  → :mod:`logging` (stdlib)
"""

from app.insurance import models, router, schemas, services

__all__ = ["models", "router", "schemas", "services"]
