# coding: utf-8
 
#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Helper classes for implementing desktop components that can monitor and control some functions
of the desktop service. It is used for Indicators, System tray icons and panel applets and
deals with all the hard work of connecting to DBus and monitoring events.
"""

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15").ugettext

import sys
import pygtk
pygtk.require('2.0')
import gtk
import subprocess
import gconf
import gobject
import shutil
import gnome15.g15globals as g15globals
import gnome15.g15screen as g15screen
import gnome15.util.g15pythonlang as g15pythonlang
import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15os as g15os
import gnome15.g15notify as g15notify
import gnome15.util.g15icontools as g15icontools
import dbus
import os.path
import operator
import xdg.DesktopEntry
import xdg.BaseDirectory

# Logging
import logging
logger = logging.getLogger(__name__)

from threading import RLock
from threading import Thread
                
icon_theme = gtk.icon_theme_get_default()
if g15globals.dev:
    icon_theme.prepend_search_path(g15globals.icons_dir)

# Private     
__browsers = { }
    
"""
Some constants
"""
AUTHORS=["Brett Smith <tanktarta@blueyonder.co.uk>", "Nuno Araujo", "Ciprian Ciubotariu", "Andrea Calabrò" ]
GPL="""
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <http://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The GNU General Public License is a free, copyleft license for
software and other kinds of works.

  The licenses for most software and other practical works are designed
to take away your freedom to share and change the works.  By contrast,
the GNU General Public License is intended to guarantee your freedom to
share and change all versions of a program--to make sure it remains free
software for all its users.  We, the Free Software Foundation, use the
GNU General Public License for most of our software; it applies also to
any other work released this way by its authors.  You can apply it to
your programs, too.

  When we speak of free software, we are referring to freedom, not
price.  Our General Public Licenses are designed to make sure that you
have the freedom to distribute copies of free software (and charge for
them if you wish), that you receive source code or can get it if you
want it, that you can change the software or use pieces of it in new
free programs, and that you know you can do these things.

  To protect your rights, we need to prevent others from denying you
these rights or asking you to surrender the rights.  Therefore, you have
certain responsibilities if you distribute copies of the software, or if
you modify it: responsibilities to respect the freedom of others.

  For example, if you distribute copies of such a program, whether
gratis or for a fee, you must pass on to the recipients the same
freedoms that you received.  You must make sure that they, too, receive
or can get the source code.  And you must show them these terms so they
know their rights.

  Developers that use the GNU GPL protect your rights with two steps:
(1) assert copyright on the software, and (2) offer you this License
giving you legal permission to copy, distribute and/or modify it.

  For the developers' and authors' protection, the GPL clearly explains
that there is no warranty for this free software.  For both users' and
authors' sake, the GPL requires that modified versions be marked as
changed, so that their problems will not be attributed erroneously to
authors of previous versions.

  Some devices are designed to deny users access to install or run
modified versions of the software inside them, although the manufacturer
can do so.  This is fundamentally incompatible with the aim of
protecting users' freedom to change the software.  The systematic
pattern of such abuse occurs in the area of products for individuals to
use, which is precisely where it is most unacceptable.  Therefore, we
have designed this version of the GPL to prohibit the practice for those
products.  If such problems arise substantially in other domains, we
stand ready to extend this provision to those domains in future versions
of the GPL, as needed to protect the freedom of users.

  Finally, every program is threatened constantly by software patents.
States should not allow patents to restrict development and use of
software on general-purpose computers, but in those that do, we wish to
avoid the special danger that patents applied to a free program could
make it effectively proprietary.  To prevent this, the GPL assures that
patents cannot be used to render the program non-free.

  The precise terms and conditions for copying, distribution and
modification follow.

                       TERMS AND CONDITIONS

  0. Definitions.

  "This License" refers to version 3 of the GNU General Public License.

  "Copyright" also means copyright-like laws that apply to other kinds of
works, such as semiconductor masks.

  "The Program" refers to any copyrightable work licensed under this
License.  Each licensee is addressed as "you".  "Licensees" and
"recipients" may be individuals or organizations.

  To "modify" a work means to copy from or adapt all or part of the work
in a fashion requiring copyright permission, other than the making of an
exact copy.  The resulting work is called a "modified version" of the
earlier work or a work "based on" the earlier work.

  A "covered work" means either the unmodified Program or a work based
on the Program.

  To "propagate" a work means to do anything with it that, without
permission, would make you directly or secondarily liable for
infringement under applicable copyright law, except executing it on a
computer or modifying a private copy.  Propagation includes copying,
distribution (with or without modification), making available to the
public, and in some countries other activities as well.

  To "convey" a work means any kind of propagation that enables other
parties to make or receive copies.  Mere interaction with a user through
a computer network, with no transfer of a copy, is not conveying.

  An interactive user interface displays "Appropriate Legal Notices"
to the extent that it includes a convenient and prominently visible
feature that (1) displays an appropriate copyright notice, and (2)
tells the user that there is no warranty for the work (except to the
extent that warranties are provided), that licensees may convey the
work under this License, and how to view a copy of this License.  If
the interface presents a list of user commands or options, such as a
menu, a prominent item in the list meets this criterion.

  1. Source Code.

  The "source code" for a work means the preferred form of the work
for making modifications to it.  "Object code" means any non-source
form of a work.

  A "Standard Interface" means an interface that either is an official
standard defined by a recognized standards body, or, in the case of
interfaces specified for a particular programming language, one that
is widely used among developers working in that language.

  The "System Libraries" of an executable work include anything, other
than the work as a whole, that (a) is included in the normal form of
packaging a Major Component, but which is not part of that Major
Component, and (b) serves only to enable use of the work with that
Major Component, or to implement a Standard Interface for which an
implementation is available to the public in source code form.  A
"Major Component", in this context, means a major essential component
(kernel, window system, and so on) of the specific operating system
(if any) on which the executable work runs, or a compiler used to
produce the work, or an object code interpreter used to run it.

  The "Corresponding Source" for a work in object code form means all
the source code needed to generate, install, and (for an executable
work) run the object code and to modify the work, including scripts to
control those activities.  However, it does not include the work's
System Libraries, or general-purpose tools or generally available free
programs which are used unmodified in performing those activities but
which are not part of the work.  For example, Corresponding Source
includes interface definition files associated with source files for
the work, and the source code for shared libraries and dynamically
linked subprograms that the work is specifically designed to require,
such as by intimate data communication or control flow between those
subprograms and other parts of the work.

  The Corresponding Source need not include anything that users
can regenerate automatically from other parts of the Corresponding
Source.

  The Corresponding Source for a work in source code form is that
same work.

  2. Basic Permissions.

  All rights granted under this License are granted for the term of
copyright on the Program, and are irrevocable provided the stated
conditions are met.  This License explicitly affirms your unlimited
permission to run the unmodified Program.  The output from running a
covered work is covered by this License only if the output, given its
content, constitutes a covered work.  This License acknowledges your
rights of fair use or other equivalent, as provided by copyright law.

  You may make, run and propagate covered works that you do not
convey, without conditions so long as your license otherwise remains
in force.  You may convey covered works to others for the sole purpose
of having them make modifications exclusively for you, or provide you
with facilities for running those works, provided that you comply with
the terms of this License in conveying all material for which you do
not control copyright.  Those thus making or running the covered works
for you must do so exclusively on your behalf, under your direction
and control, on terms that prohibit them from making any copies of
your copyrighted material outside their relationship with you.

  Conveying under any other circumstances is permitted solely under
the conditions stated below.  Sublicensing is not allowed; section 10
makes it unnecessary.

  3. Protecting Users' Legal Rights From Anti-Circumvention Law.

  No covered work shall be deemed part of an effective technological
measure under any applicable law fulfilling obligations under article
11 of the WIPO copyright treaty adopted on 20 December 1996, or
similar laws prohibiting or restricting circumvention of such
measures.

  When you convey a covered work, you waive any legal power to forbid
circumvention of technological measures to the extent such circumvention
is effected by exercising rights under this License with respect to
the covered work, and you disclaim any intention to limit operation or
modification of the work as a means of enforcing, against the work's
users, your or third parties' legal rights to forbid circumvention of
technological measures.

  4. Conveying Verbatim Copies.

  You may convey verbatim copies of the Program's source code as you
receive it, in any medium, provided that you conspicuously and
appropriately publish on each copy an appropriate copyright notice;
keep intact all notices stating that this License and any
non-permissive terms added in accord with section 7 apply to the code;
keep intact all notices of the absence of any warranty; and give all
recipients a copy of this License along with the Program.

  You may charge any price or no price for each copy that you convey,
and you may offer support or warranty protection for a fee.

  5. Conveying Modified Source Versions.

  You may convey a work based on the Program, or the modifications to
produce it from the Program, in the form of source code under the
terms of section 4, provided that you also meet all of these conditions:

    a) The work must carry prominent notices stating that you modified
    it, and giving a relevant date.

    b) The work must carry prominent notices stating that it is
    released under this License and any conditions added under section
    7.  This requirement modifies the requirement in section 4 to
    "keep intact all notices".

    c) You must license the entire work, as a whole, under this
    License to anyone who comes into possession of a copy.  This
    License will therefore apply, along with any applicable section 7
    additional terms, to the whole of the work, and all its parts,
    regardless of how they are packaged.  This License gives no
    permission to license the work in any other way, but it does not
    invalidate such permission if you have separately received it.

    d) If the work has interactive user interfaces, each must display
    Appropriate Legal Notices; however, if the Program has interactive
    interfaces that do not display Appropriate Legal Notices, your
    work need not make them do so.

  A compilation of a covered work with other separate and independent
works, which are not by their nature extensions of the covered work,
and which are not combined with it such as to form a larger program,
in or on a volume of a storage or distribution medium, is called an
"aggregate" if the compilation and its resulting copyright are not
used to limit the access or legal rights of the compilation's users
beyond what the individual works permit.  Inclusion of a covered work
in an aggregate does not cause this License to apply to the other
parts of the aggregate.

  6. Conveying Non-Source Forms.

  You may convey a covered work in object code form under the terms
of sections 4 and 5, provided that you also convey the
machine-readable Corresponding Source under the terms of this License,
in one of these ways:

    a) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by the
    Corresponding Source fixed on a durable physical medium
    customarily used for software interchange.

    b) Convey the object code in, or embodied in, a physical product
    (including a physical distribution medium), accompanied by a
    written offer, valid for at least three years and valid for as
    long as you offer spare parts or customer support for that product
    model, to give anyone who possesses the object code either (1) a
    copy of the Corresponding Source for all the software in the
    product that is covered by this License, on a durable physical
    medium customarily used for software interchange, for a price no
    more than your reasonable cost of physically performing this
    conveying of source, or (2) access to copy the
    Corresponding Source from a network server at no charge.

    c) Convey individual copies of the object code with a copy of the
    written offer to provide the Corresponding Source.  This
    alternative is allowed only occasionally and noncommercially, and
    only if you received the object code with such an offer, in accord
    with subsection 6b.

    d) Convey the object code by offering access from a designated
    place (gratis or for a charge), and offer equivalent access to the
    Corresponding Source in the same way through the same place at no
    further charge.  You need not require recipients to copy the
    Corresponding Source along with the object code.  If the place to
    copy the object code is a network server, the Corresponding Source
    may be on a different server (operated by you or a third party)
    that supports equivalent copying facilities, provided you maintain
    clear directions next to the object code saying where to find the
    Corresponding Source.  Regardless of what server hosts the
    Corresponding Source, you remain obligated to ensure that it is
    available for as long as needed to satisfy these requirements.

    e) Convey the object code using peer-to-peer transmission, provided
    you inform other peers where the object code and Corresponding
    Source of the work are being offered to the general public at no
    charge under subsection 6d.

  A separable portion of the object code, whose source code is excluded
from the Corresponding Source as a System Library, need not be
included in conveying the object code work.

  A "User Product" is either (1) a "consumer product", which means any
tangible personal property which is normally used for personal, family,
or household purposes, or (2) anything designed or sold for incorporation
into a dwelling.  In determining whether a product is a consumer product,
doubtful cases shall be resolved in favor of coverage.  For a particular
product received by a particular user, "normally used" refers to a
typical or common use of that class of product, regardless of the status
of the particular user or of the way in which the particular user
actually uses, or expects or is expected to use, the product.  A product
is a consumer product regardless of whether the product has substantial
commercial, industrial or non-consumer uses, unless such uses represent
the only significant mode of use of the product.

  "Installation Information" for a User Product means any methods,
procedures, authorization keys, or other information required to install
and execute modified versions of a covered work in that User Product from
a modified version of its Corresponding Source.  The information must
suffice to ensure that the continued functioning of the modified object
code is in no case prevented or interfered with solely because
modification has been made.

  If you convey an object code work under this section in, or with, or
specifically for use in, a User Product, and the conveying occurs as
part of a transaction in which the right of possession and use of the
User Product is transferred to the recipient in perpetuity or for a
fixed term (regardless of how the transaction is characterized), the
Corresponding Source conveyed under this section must be accompanied
by the Installation Information.  But this requirement does not apply
if neither you nor any third party retains the ability to install
modified object code on the User Product (for example, the work has
been installed in ROM).

  The requirement to provide Installation Information does not include a
requirement to continue to provide support service, warranty, or updates
for a work that has been modified or installed by the recipient, or for
the User Product in which it has been modified or installed.  Access to a
network may be denied when the modification itself materially and
adversely affects the operation of the network or violates the rules and
protocols for communication across the network.

  Corresponding Source conveyed, and Installation Information provided,
in accord with this section must be in a format that is publicly
documented (and with an implementation available to the public in
source code form), and must require no special password or key for
unpacking, reading or copying.

  7. Additional Terms.

  "Additional permissions" are terms that supplement the terms of this
License by making exceptions from one or more of its conditions.
Additional permissions that are applicable to the entire Program shall
be treated as though they were included in this License, to the extent
that they are valid under applicable law.  If additional permissions
apply only to part of the Program, that part may be used separately
under those permissions, but the entire Program remains governed by
this License without regard to the additional permissions.

  When you convey a copy of a covered work, you may at your option
remove any additional permissions from that copy, or from any part of
it.  (Additional permissions may be written to require their own
removal in certain cases when you modify the work.)  You may place
additional permissions on material, added by you to a covered work,
for which you have or can give appropriate copyright permission.

  Notwithstanding any other provision of this License, for material you
add to a covered work, you may (if authorized by the copyright holders of
that material) supplement the terms of this License with terms:

    a) Disclaiming warranty or limiting liability differently from the
    terms of sections 15 and 16 of this License; or

    b) Requiring preservation of specified reasonable legal notices or
    author attributions in that material or in the Appropriate Legal
    Notices displayed by works containing it; or

    c) Prohibiting misrepresentation of the origin of that material, or
    requiring that modified versions of such material be marked in
    reasonable ways as different from the original version; or

    d) Limiting the use for publicity purposes of names of licensors or
    authors of the material; or

    e) Declining to grant rights under trademark law for use of some
    trade names, trademarks, or service marks; or

    f) Requiring indemnification of licensors and authors of that
    material by anyone who conveys the material (or modified versions of
    it) with contractual assumptions of liability to the recipient, for
    any liability that these contractual assumptions directly impose on
    those licensors and authors.

  All other non-permissive additional terms are considered "further
restrictions" within the meaning of section 10.  If the Program as you
received it, or any part of it, contains a notice stating that it is
governed by this License along with a term that is a further
restriction, you may remove that term.  If a license document contains
a further restriction but permits relicensing or conveying under this
License, you may add to a covered work material governed by the terms
of that license document, provided that the further restriction does
not survive such relicensing or conveying.

  If you add terms to a covered work in accord with this section, you
must place, in the relevant source files, a statement of the
additional terms that apply to those files, or a notice indicating
where to find the applicable terms.

  Additional terms, permissive or non-permissive, may be stated in the
form of a separately written license, or stated as exceptions;
the above requirements apply either way.

  8. Termination.

  You may not propagate or modify a covered work except as expressly
provided under this License.  Any attempt otherwise to propagate or
modify it is void, and will automatically terminate your rights under
this License (including any patent licenses granted under the third
paragraph of section 11).

  However, if you cease all violation of this License, then your
license from a particular copyright holder is reinstated (a)
provisionally, unless and until the copyright holder explicitly and
finally terminates your license, and (b) permanently, if the copyright
holder fails to notify you of the violation by some reasonable means
prior to 60 days after the cessation.

  Moreover, your license from a particular copyright holder is
reinstated permanently if the copyright holder notifies you of the
violation by some reasonable means, this is the first time you have
received notice of violation of this License (for any work) from that
copyright holder, and you cure the violation prior to 30 days after
your receipt of the notice.

  Termination of your rights under this section does not terminate the
licenses of parties who have received copies or rights from you under
this License.  If your rights have been terminated and not permanently
reinstated, you do not qualify to receive new licenses for the same
material under section 10.

  9. Acceptance Not Required for Having Copies.

  You are not required to accept this License in order to receive or
run a copy of the Program.  Ancillary propagation of a covered work
occurring solely as a consequence of using peer-to-peer transmission
to receive a copy likewise does not require acceptance.  However,
nothing other than this License grants you permission to propagate or
modify any covered work.  These actions infringe copyright if you do
not accept this License.  Therefore, by modifying or propagating a
covered work, you indicate your acceptance of this License to do so.

  10. Automatic Licensing of Downstream Recipients.

  Each time you convey a covered work, the recipient automatically
receives a license from the original licensors, to run, modify and
propagate that work, subject to this License.  You are not responsible
for enforcing compliance by third parties with this License.

  An "entity transaction" is a transaction transferring control of an
organization, or substantially all assets of one, or subdividing an
organization, or merging organizations.  If propagation of a covered
work results from an entity transaction, each party to that
transaction who receives a copy of the work also receives whatever
licenses to the work the party's predecessor in interest had or could
give under the previous paragraph, plus a right to possession of the
Corresponding Source of the work from the predecessor in interest, if
the predecessor has it or can get it with reasonable efforts.

  You may not impose any further restrictions on the exercise of the
rights granted or affirmed under this License.  For example, you may
not impose a license fee, royalty, or other charge for exercise of
rights granted under this License, and you may not initiate litigation
(including a cross-claim or counterclaim in a lawsuit) alleging that
any patent claim is infringed by making, using, selling, offering for
sale, or importing the Program or any portion of it.

  11. Patents.

  A "contributor" is a copyright holder who authorizes use under this
License of the Program or a work on which the Program is based.  The
work thus licensed is called the contributor's "contributor version".

  A contributor's "essential patent claims" are all patent claims
owned or controlled by the contributor, whether already acquired or
hereafter acquired, that would be infringed by some manner, permitted
by this License, of making, using, or selling its contributor version,
but do not include claims that would be infringed only as a
consequence of further modification of the contributor version.  For
purposes of this definition, "control" includes the right to grant
patent sublicenses in a manner consistent with the requirements of
this License.

  Each contributor grants you a non-exclusive, worldwide, royalty-free
patent license under the contributor's essential patent claims, to
make, use, sell, offer for sale, import and otherwise run, modify and
propagate the contents of its contributor version.

  In the following three paragraphs, a "patent license" is any express
agreement or commitment, however denominated, not to enforce a patent
(such as an express permission to practice a patent or covenant not to
sue for patent infringement).  To "grant" such a patent license to a
party means to make such an agreement or commitment not to enforce a
patent against the party.

  If you convey a covered work, knowingly relying on a patent license,
and the Corresponding Source of the work is not available for anyone
to copy, free of charge and under the terms of this License, through a
publicly available network server or other readily accessible means,
then you must either (1) cause the Corresponding Source to be so
available, or (2) arrange to deprive yourself of the benefit of the
patent license for this particular work, or (3) arrange, in a manner
consistent with the requirements of this License, to extend the patent
license to downstream recipients.  "Knowingly relying" means you have
actual knowledge that, but for the patent license, your conveying the
covered work in a country, or your recipient's use of the covered work
in a country, would infringe one or more identifiable patents in that
country that you have reason to believe are valid.

  If, pursuant to or in connection with a single transaction or
arrangement, you convey, or propagate by procuring conveyance of, a
covered work, and grant a patent license to some of the parties
receiving the covered work authorizing them to use, propagate, modify
or convey a specific copy of the covered work, then the patent license
you grant is automatically extended to all recipients of the covered
work and works based on it.

  A patent license is "discriminatory" if it does not include within
the scope of its coverage, prohibits the exercise of, or is
conditioned on the non-exercise of one or more of the rights that are
specifically granted under this License.  You may not convey a covered
work if you are a party to an arrangement with a third party that is
in the business of distributing software, under which you make payment
to the third party based on the extent of your activity of conveying
the work, and under which the third party grants, to any of the
parties who would receive the covered work from you, a discriminatory
patent license (a) in connection with copies of the covered work
conveyed by you (or copies made from those copies), or (b) primarily
for and in connection with specific products or compilations that
contain the covered work, unless you entered into that arrangement,
or that patent license was granted, prior to 28 March 2007.

  Nothing in this License shall be construed as excluding or limiting
any implied license or other defenses to infringement that may
otherwise be available to you under applicable patent law.

  12. No Surrender of Others' Freedom.

  If conditions are imposed on you (whether by court order, agreement or
otherwise) that contradict the conditions of this License, they do not
excuse you from the conditions of this License.  If you cannot convey a
covered work so as to satisfy simultaneously your obligations under this
License and any other pertinent obligations, then as a consequence you may
not convey it at all.  For example, if you agree to terms that obligate you
to collect a royalty for further conveying from those to whom you convey
the Program, the only way you could satisfy both those terms and this
License would be to refrain entirely from conveying the Program.

  13. Use with the GNU Affero General Public License.

  Notwithstanding any other provision of this License, you have
permission to link or combine any covered work with a work licensed
under version 3 of the GNU Affero General Public License into a single
combined work, and to convey the resulting work.  The terms of this
License will continue to apply to the part which is the covered work,
but the special requirements of the GNU Affero General Public License,
section 13, concerning interaction through a network will apply to the
combination as such.

  14. Revised Versions of this License.

  The Free Software Foundation may publish revised and/or new versions of
the GNU General Public License from time to time.  Such new versions will
be similar in spirit to the present version, but may differ in detail to
address new problems or concerns.

  Each version is given a distinguishing version number.  If the
Program specifies that a certain numbered version of the GNU General
Public License "or any later version" applies to it, you have the
option of following the terms and conditions either of that numbered
version or of any later version published by the Free Software
Foundation.  If the Program does not specify a version number of the
GNU General Public License, you may choose any version ever published
by the Free Software Foundation.

  If the Program specifies that a proxy can decide which future
versions of the GNU General Public License can be used, that proxy's
public statement of acceptance of a version permanently authorizes you
to choose that version for the Program.

  Later license versions may give you additional or different
permissions.  However, no additional obligations are imposed on any
author or copyright holder as a result of your choosing to follow a
later version.

  15. Disclaimer of Warranty.

  THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY
APPLICABLE LAW.  EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT
HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY
OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE.  THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM
IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF
ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

  16. Limitation of Liability.

  IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS
THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY
GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF
DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD
PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS),
EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF
SUCH DAMAGES.

  17. Interpretation of Sections 15 and 16.

  If the disclaimer of warranty and limitation of liability provided
above cannot be given local legal effect according to their terms,
reviewing courts shall apply local law that most closely approximates
an absolute waiver of all civil liability in connection with the
Program, unless a warranty or assumption of liability accompanies a
copy of the Program in return for a fee.

                     END OF TERMS AND CONDITIONS

            How to Apply These Terms to Your New Programs

  If you develop a new program, and you want it to be of the greatest
possible use to the public, the best way to achieve this is to make it
free software which everyone can redistribute and change under these terms.

  To do so, attach the following notices to the program.  It is safest
to attach them to the start of each source file to most effectively
state the exclusion of warranty; and each file should have at least
the "copyright" line and a pointer to where the full notice is found.

    <one line to give the program's name and a brief idea of what it does.>
    Copyright (C) <year>  <name of author>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Also add information on how to contact you by electronic and paper mail.

  If the program does terminal interaction, make it output a short
notice like this when it starts in an interactive mode:

    <program>  Copyright (C) <year>  <name of author>
    This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.

The hypothetical commands `show w' and `show c' should show the appropriate
parts of the General Public License.  Of course, your program's commands
might be different; for a GUI interface, you would use an "about box".

  You should also get your employer (if you work as a programmer) or school,
if any, to sign a "copyright disclaimer" for the program, if necessary.
For more information on this, and how to apply and follow the GNU GPL, see
<http://www.gnu.org/licenses/>.

  The GNU General Public License does not permit incorporating your program
into proprietary programs.  If your program is a subroutine library, you
may consider it more useful to permit linking proprietary applications with
the library.  If this is what you want to do, use the GNU Lesser General
Public License instead of this License.  But first, please read
<http://www.gnu.org/philosophy/why-not-lgpl.html>.
"""

def autostart_path_for(application_name):
    """
    Returns the autostart path of the application_name desktop file
    """
    return os.path.join(xdg.BaseDirectory.xdg_config_home,
                        "autostart",
                        "%s.desktop" % application_name)
    
def is_desktop_application_installed(application_name):
    """
    Get if a desktop file is installed for a particular application
    
    Keyword arguments:
    application_name    --    name of application
    """
    for directory in xdg.BaseDirectory.xdg_config_dirs:
        desktop_file = os.path.join(directory,
                                    "autostart",
                                    "%s.desktop" % application_name)
        if os.path.exists(desktop_file):
            return True
    return False

def is_autostart_application(application_name):
    """
    Get whether the application is set to autostart
    """
    installed  = is_desktop_application_installed(application_name)
    path = autostart_path_for(application_name)
    if os.path.exists(path):
        desktop_entry = xdg.DesktopEntry.DesktopEntry(path)
        autostart = len(desktop_entry.get('X-GNOME-Autostart-enabled')) == 0 or desktop_entry.get('X-GNOME-Autostart-enabled', type="boolean")
        hidden = desktop_entry.getHidden()
        return autostart and not hidden
    else:
        # There is no config file, so enabled if installed
        return installed

def set_autostart_application(application_name, enabled):
    """
    Set whether an application is set to autostart
    
    Keyword arguments:
    application_name    -- application name
    enabled             -- enabled or not
    """
    path = autostart_path_for(application_name)
    if enabled and os.path.exists(path):
        os.remove(path)
    elif not enabled:
        app_path = "/etc/xdg/autostart/%s.desktop" % application_name
        if not os.path.exists(path):
            shutil.copy(app_path, path)
        desktop_entry = xdg.DesktopEntry.DesktopEntry(path)
        desktop_entry.set("X-GNOME-Autostart-enabled", "false")
        desktop_entry.set("Hidden", "false")
        desktop_entry.write()

def get_desktop():
    '''
    Utility function to get the name of the current desktop environment. The list
    of detectable desktop environments is not complete, but hopefully this will
    improve over time. Currently no attempt is made to determine the version of
    the desktop in use.
    
    Will return :-
    
    gnome          GNOME Desktop
    gnome-shell    GNOME Shell Desktop 
    kde            KDE 
    [None]         No known desktop  
    '''
    
    evars = os.environ
    
    # GNOME Shell (need a better way)
    if ( "DESKTOP_SESSION" in evars and evars["DESKTOP_SESSION"] == "gnome-shell" ) or \
       ( "GJS_DEBUG_OUTPUT" in evars ):
            return "gnome-shell"
    
    # XDG_CURRENT_DESKTOP
    dt = { "LXDE" : "lxde", "GNOME" : "gnome"}
    if "XDG_CURRENT_DESKTOP" in evars:
        val = evars["XDG_CURRENT_DESKTOP"]
        if val in dt:
            return dt[val]
    
    # Environment variables that suggest the use of GNOME
    for i in [ "GNOME_DESKTOP_SESSION_ID", "GNOME_KEYRING_CONTROL" ]:
        if i in evars:
            return "gnome"
    
    # Environment variables that suggest the use of KDE
    for i in [ "KDE_FULL_SESSION", "KDE_SESSION_VERSION", "KDE_SESSION_UID" ]:
        if i in evars:
            return "kde"
    
    # Environment variables that suggest the use of LXDE
    for i in [ "_LXSESSION_PID" ]:
        if i in evars:
            return "lxde"
        
def is_shell_extension_installed(extension):
    """
    Get whether a GNOME Shell extension is installed.
    
    Keyword arguments:
    extension        --    extension name
    """
    for prefix in xdg.BaseDirectory.xdg_data_dirs:
        extension_path = os.path.join(prefix, "gnome-shell", "extensions", extension)
        if os.path.exists(extension_path):
            return True
    return False
        
def is_gnome_shell_extension_enabled(extension):
    """
    Get whether a GNOME Shell extension is enabled. This uses the
    gsettings command. Python GSettings bindings (GObject introspected ones)
    are not used, as well already use PyGTK and the two don't mix
    
    Keyword arguments:
    extension        --    extension name
    """
    status, text = g15os.get_command_output("gsettings get org.gnome.shell enabled-extensions")
    if status == 0:
        try:
            return extension in eval(text)
        except Exception as e:
            logger.debug("Failed testing if extension is enabled.", exc_info = e)
            
    return False
        
def set_gnome_shell_extension_enabled(extension, enabled):
    """
    Enable or disable a GNOME Shell extension is enabled. This uses the
    gsettings command. Python GSettings bindings (GObject introspected ones)
    are not used, as well already use PyGTK and the two don't mix
    
    Keyword arguments:
    extension        --    extension name
    enabled          --    enabled
    """
    status, text = g15os.get_command_output("gsettings get org.gnome.shell enabled-extensions")
    if status == 0:
        try:
            extensions = eval(text)
        except Exception as e:
            logger.debug('No gnome-shell extensions enabled.', exc_info = e)
            # No extensions available, so init an empty array
            extensions = []
            pass
        contains = extension in extensions
        if contains and not enabled:
            extensions.remove(extension)
        elif not contains and enabled:
            extensions.append(extension)
        s = ""
        for c in extensions:
            if len(s) >0:
                s += ","
            s += "'%s'" % c
        try:
            status, text = g15os.get_command_output("gsettings set org.gnome.shell enabled-extensions \"[%s]\"" % s)
        except Exception as e:
            logger.debug("Failed to set extension enabled.", exc_info = e)
            
def browse(url):
    """
    Open the configured browser
    
    Keyword arguments:
    url        -- URL
    """
    b = g15gconf.get_string_or_default(gconf.client_get_default(), \
                                      "/apps/gnome15/browser", "default")
    if not b in __browsers and not b == "default":
        logger.warning("Could not find browser %s, falling back to default", b)
        b = "default"
    if not b in __browsers:
        raise Exception("Could not find browser %s" % b)
    __browsers[b].browse(url)

def add_browser(browser):
    """
    Register a new browser. The object must extend G15Browser
    
    Keyword arguments:
    browser        -- browser object.
    """
    if browser.browser_id in __browsers:
        raise Exception("Browser already registered")
    if not isinstance(browser, G15Browser):
        raise Exception("Not a G15Browser instance")
    __browsers[browser.browser_id] = browser
        
class G15Browser():
    def __init__(self, browser_id, name):
        self.name = name
        self.browser_id = browser_id
    
    def browse(self, url):
        raise Exception("Not implemented")

class G15DefaultBrowser(G15Browser):
    def __init__(self):
        G15Browser.__init__(self, "default", _("Default system browser"))
    
    def browse(self, url):
        logger.info("xdg-open '%s'", url)
        subprocess.Popen(['xdg-open', url])
        
add_browser(G15DefaultBrowser())
    
class G15AbstractService(Thread):
    
    def __init__(self):
        Thread.__init__(self)        
        # Start this thread, which runs the gobject loop. This is 
        # run first, and in a thread, as starting the Gnome15 will send
        # DBUS events (which are sent on the loop). 
        self.loop = gobject.MainLoop()
        self.start()
        
    def start_loop(self):
        logger.info("Starting GLib loop")
        g15pythonlang.set_gobject_thread()
        try:
            self.loop.run()
        except Exception as e:
            logger.debug('Error while running GLib loop', exc_info = e)
        logger.info("Exited GLib loop")
        
    def start_service(self):
        raise Exception("Not implemented")
        
    def run(self):        
        # Now start the service, which will connect to all devices and
        # start their plugins
        self.start_service()
                
    
class G15Screen():
    """
    Client side representation of a remote screen. Holds general details such
    as model name, UID and the pages that screen is currently showing.
    """
    
    def __init__(self, path, device_model_fullname, device_uid):
        self.path = path
        self.device_model_fullname = device_model_fullname
        self.device_uid = device_uid
        self.items = {}
        self.message = None

class G15DesktopComponent():
    """
    Helper class for implementing desktop components that can monitor and control some functions
    of the desktop service. It is used for Indicators, System tray icons and panel applets and
    deals with all the hard work of connecting to DBus and monitoring events.
    """
    
    def __init__(self):
        self.screens = {}
        self.service = None
        self.start_service_item = None
        self.attention_item = None
        self.pages = []   
        self.lock = RLock()
        self.attention_messages = {}
        self.connected = False
        
        # Connect to DBus and GConf
        self.conf_client = gconf.client_get_default()
        self.session_bus = dbus.SessionBus()

        # Enable monitoring of Gnome15 GConf settings
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        
        # Initialise desktop component
        self.initialise_desktop_component()     
        self.icons_changed()
        
    def start_service(self):
        """
        Start the desktop component. An attempt will be made to connect to Gnome15 over 
        DBus. If this fails, the component should stay active until the service becomes
        available.
        """
        
        # Try and connect to the service now
        try :
            self._connect()        
        except dbus.exceptions.DBusException as e:
            logger.debug("Error while starting the service.", exc_info = e)
            self._disconnect()
        
        # Start watching various events
        self.conf_client.notify_add("/apps/gnome15/indicate_only_on_error", self._indicator_options_changed)
        gtk_icon_theme = gtk.icon_theme_get_default()
        gtk_icon_theme.connect("changed", self._theme_changed)

        # Watch for Gnome15 starting and stopping
        self.session_bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')  
        
    """
    Pulic functions
    """
    def is_attention(self):
        return len(self.attention_messages) > 0
    
    def get_icon_path(self, icon_name):
        """
        Helper function to get an icon path or it's name, given the name. 
        """
        if g15globals.dev:
            # Because the icons aren't installed in this mode, they must be provided
            # using the full filename. Unfortunately this means scaling may be a bit
            # blurry in the indicator applet
            path = g15icontools.get_icon_path(icon_name, 128)
            logger.debug("Dev mode icon %s is at %s", icon_name, path)
            return path
        else:
            if not isinstance(icon_name, list):
                icon_name = [ icon_name ]
            for i in icon_name:
                p = g15icontools.get_icon_path(i, -1)
                if p is not None:
                    return i
             
    def show_configuration(self, arg = None):
        """
        Show the configuration user interface
        """        
        g15os.run_script("g15-config")
        
    def stop_desktop_service(self, arg = None):
        """
        Stop the desktop service
        """ 
        self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service').Stop()   
        
    def start_desktop_service(self, arg = None):
        """
        Start the desktop service
        """    
        g15os.run_script("g15-desktop-service", ["-f"])
        
    def show_page(self, path):
        """
        Show a page, given its path
        """
        self.session_bus.get_object('org.gnome15.Gnome15', path).CycleTo()
        
    def check_attention(self):
        """
        Check the current state of attention, either clearing it or setting it and displaying
        a new message
        """
        if len(self.attention_messages) == 0:
            self.clear_attention()      
        else:
            for i in self.attention_messages:
                message = self.attention_messages[i]
                self.attention(message)
                break
        
    """
    Functions that must be implemented
    """
        
    def initialise_desktop_component(self):
        """
        This function is called during construction and should create initial desktop component
        """ 
        raise Exception("Not implemented")
    
    def rebuild_desktop_component(self):
        """
        This function is called every time the list of screens or pages changes 
        in someway. The desktop component should be rebuilt to reflect the
        new state
        """
        raise Exception("Not implemented")
    
    def clear_attention(self):
        """
        Clear any "Attention" state indicators
        """
        raise Exception("Not implemented")
        
    def attention(self, message = None):
        """
        Display an "Attention" state indicator with a message
        
        Keyword Arguments:
        message    --    message to display
        """
        raise Exception("Not implemented")
    
    def icons_changed(self):
        """
        Invoked once a start up, and then whenever the desktop icon theme changes. Implementations
        should do whatever required to change any themed icons they are displayed
        """
        raise Exception("Not implemented")
    
    def options_changed(self):
        """
        Invoked when any global desktop component options change.
        """
        raise Exception("Not implemented")
        
    '''
    DBUS Event Callbacks
    ''' 
    def _name_owner_changed(self, name, old_owner, new_owner):
        if name == "org.gnome15.Gnome15":
            if old_owner == "":
                if self.service == None:
                    self._connect()
            else:
                if self.service != None:
                    self.connected = False
                    self._disconnect()
        
    def _page_created(self, page_path, page_title, path = None):
        screen_path = path
        logger.debug("Page created (%s) %s = %s", screen_path, page_path, page_title)
        page = self.session_bus.get_object('org.gnome15.Gnome15', page_path )
        self.lock.acquire()
        try :
            if page.GetPriority() >= g15screen.PRI_LOW:
                self._add_page(screen_path, page_path, page)
        finally :
            self.lock.release()
        
    def _page_title_changed(self, page_path, title, path = None):
        screen_path = path
        self.lock.acquire()
        try :
            self.screens[screen_path].items[page_path] = title
            self.rebuild_desktop_component()
        finally :
            self.lock.release()
    
    def _page_deleting(self, page_path, path = None):
        screen_path = path
        self.lock.acquire()
        logger.debug("Destroying page (%s) %s", screen_path, page_path)
        try :
            items = self.screens[screen_path].items
            if page_path in items:
                del items[page_path]
                self.rebuild_desktop_component()
        finally :
            self.lock.release()
        
    def _attention_cleared(self, path = None):
        screen_path = path
        if screen_path in self.attention_messages:
            del self.attention_messages[screen_path]
            self.rebuild_desktop_component()
        
    def _attention_requested(self, message = None, path = None):
        screen_path = path
        if not screen_path in self.attention_messages:
            self.attention_messages[screen_path] = message
            self.rebuild_desktop_component()
        
    """
    Private
    """
            
    def _enable(self, widget, device):
        device.Enable()
        
    def _disable(self, widget, device):
        device.Disable()
        
    def _cycle_screens_option_changed(self, client, connection_id, entry, args):
        self.rebuild_desktop_component()
        
    def _remove_screen(self, screen_path):
        print "*** removing %s from %s" % ( str(screen_path), str(self.screens))
        if screen_path in self.screens:
            try :
                del self.screens[screen_path]
            except dbus.DBusException as e:
                logger.debug("Error removing screen '%s'", screen_path, exc_info = e)
                pass
        self.rebuild_desktop_component()
        
    def _add_screen(self, screen_path):
        logger.debug("Screen added %s", screen_path)
        remote_screen = self.session_bus.get_object('org.gnome15.Gnome15', screen_path)
        ( device_uid, device_model_name, device_usb_id, device_model_fullname ) = remote_screen.GetDeviceInformation()
        screen = G15Screen(screen_path, device_model_fullname, device_uid)        
        self.screens[screen_path] = screen
        if remote_screen.IsAttentionRequested():
            screen.message = remote_screen.GetMessage()
        
    def _device_added(self, screen_path):
        self.rebuild_desktop_component()
        
    def _device_removed(self, screen_path):
        self.rebuild_desktop_component()                                
        
    def _connect(self):
        logger.debug("Connecting")
        self._reset_attention()
        self.service = self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service')
        self.connected = True
        logger.debug("Connected")
                
        # Load the initial screens
        self.lock.acquire()
        try : 
            for screen_path in self.service.GetScreens():
                logger.debug("Adding %s", screen_path)
                self._add_screen(screen_path)
                remote_screen = self.session_bus.get_object('org.gnome15.Gnome15', screen_path)
                for page_path in remote_screen.GetPages():
                    page = self.session_bus.get_object('org.gnome15.Gnome15', page_path)
                    if page.GetPriority() >= g15screen.PRI_LOW and page.GetPriority() < g15screen.PRI_HIGH:
                        self._add_page(screen_path, page_path, page)
        finally :
            self.lock.release()
        
        # Listen for events
        self.session_bus.add_signal_receiver(self._device_added, dbus_interface = "org.gnome15.Service", signal_name = "DeviceAdded")
        self.session_bus.add_signal_receiver(self._device_removed, dbus_interface = "org.gnome15.Service", signal_name = "DeviceRemoved")
        self.session_bus.add_signal_receiver(self._add_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenAdded")
        self.session_bus.add_signal_receiver(self._remove_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenRemoved")
        self.session_bus.add_signal_receiver(self._page_created, dbus_interface = "org.gnome15.Screen", signal_name = "PageCreated",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._page_title_changed, dbus_interface = "org.gnome15.Screen", signal_name = "PageTitleChanged",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._page_deleting, dbus_interface = "org.gnome15.Screen", signal_name = "PageDeleting",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._attention_requested, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionRequested",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._attention_cleared, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionCleared",  path_keyword = 'path')
            
        # We are now connected, so remove the start service menu item and allow cycling
        self.rebuild_desktop_component()
        
    def _disconnect(self):
        logger.debug("Disconnecting")                  
        self.session_bus.remove_signal_receiver(self._device_added, dbus_interface = "org.gnome15.Service", signal_name = "DeviceAdded")
        self.session_bus.remove_signal_receiver(self._device_removed, dbus_interface = "org.gnome15.Service", signal_name = "DeviceRemoved")
        self.session_bus.remove_signal_receiver(self._add_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenAdded")
        self.session_bus.remove_signal_receiver(self._remove_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenRemoved")
        self.session_bus.remove_signal_receiver(self._page_created, dbus_interface = "org.gnome15.Screen", signal_name = "PageCreated")
        self.session_bus.remove_signal_receiver(self._page_title_changed, dbus_interface = "org.gnome15.Screen", signal_name = "PageTitleChanged")
        self.session_bus.remove_signal_receiver(self._page_deleting, dbus_interface = "org.gnome15.Screen", signal_name = "PageDeleting")
        self.session_bus.remove_signal_receiver(self._attention_requested, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionRequested")
        self.session_bus.remove_signal_receiver(self._attention_cleared, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionCleared")
             
        if self.service != None and self.connected:
            for screen_path in dict(self.screens):
                self._remove_screen(screen_path)
        
        self._reset_attention()
        self._attention_requested("service", "g15-desktop-service is not running.")
            
        self.service = None  
        self.connected = False 
        self.rebuild_desktop_component()      
        
    def _reset_attention(self):
        self.attention_messages = {}
        self.rebuild_desktop_component()
            
    def _add_page(self, screen_path, page_path, page):
        logger.debug("Adding page %s to %s", page_path, screen_path)
        items = self.screens[screen_path].items
        if not page_path in items:
            items[page_path] = page.GetTitle()
            self.rebuild_desktop_component()
        
    def _indicator_options_changed(self, client, connection_id, entry, args):
        self.options_changed()
    
    def _theme_changed(self, theme):
        self.icons_changed()
        
        
class G15GtkMenuPanelComponent(G15DesktopComponent):
    
    def __init__(self):
        self.screen_number = 0
        self.devices = []
        self.notify_message = None
        G15DesktopComponent.__init__(self)
        
    def about_info(self, widget):     
        about = gtk.AboutDialog()
        about.set_name("Gnome15")
        about.set_version(g15globals.version)
        about.set_license(GPL)
        about.set_authors(AUTHORS)
        about.set_documenters(["Brett Smith <tanktarta@blueyonder.co.uk>"])
        about.set_logo(gtk.gdk.pixbuf_new_from_file(g15icontools.get_app_icon(self.conf_client, "gnome15", 128)))
        about.set_comments(_("Desktop integration for Logitech 'G' keyboards."))
        about.run()
        about.hide()
        
    def scroll_event(self, widget, event):
        
        direction = event.direction
        if direction == gtk.gdk.SCROLL_UP:
            screen = self._get_active_screen_object()
            self._close_notify_message()
            screen.ClearPopup() 
            screen.Cycle(1)
        elif direction == gtk.gdk.SCROLL_DOWN:
            screen = self._get_active_screen_object()
            self._close_notify_message()
            screen.ClearPopup() 
            screen.Cycle(-1)
        else:
            """
            If there is only one device, right scroll cycles the backlight color,
            otherwise toggle between the devices (used to select what to scroll with up
            and down) 
            """
            if direction == gtk.gdk.SCROLL_LEFT:
                self._get_active_screen_object().CycleKeyboard(-1)
            elif direction == gtk.gdk.SCROLL_RIGHT:
                if len(self.screens) > 1:
                    if self.screen_number >= len(self.screens) - 1:
                        self.screen_number = 0
                    else:
                        self.screen_number += 1
                        
                    self._set_active_screen_number()
                else:
                    self._get_active_screen_object().CycleKeyboard(1)
            
    def rebuild_desktop_component(self):
        logger.debug("Removing old menu items")
        for item in self.last_items:
            item.get_parent().remove(item)
            item.destroy()
            
        self.last_items = []
        i = 0
        
        # Remove the notify handles used for the previous cycle components
        logger.debug("Removing old notify handles")
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)
        self.notify_handles = []
        
        logger.debug("Building new menu")
        if self.service and self.connected:
            
            item = gtk.MenuItem(_("Stop Desktop Service"))
            item.connect("activate", self.stop_desktop_service)
            self.add_service_item(item)
            self.add_service_item(gtk.MenuItem())
        
            try:
                devices = self.service.GetDevices()
                for device_path in devices:
                    remote_device = self.session_bus.get_object('org.gnome15.Gnome15', device_path)
                    screen_path = remote_device.GetScreen()
                    
                    screen = self.screens[screen_path] if len(screen_path) > 0 and screen_path in self.screens else None
                    
                    if screen:
                        if i > 0:
                            logger.debug("Adding separator")
                            self._append_item(gtk.MenuItem())
                        # Disable
                        if len(devices) > 1:
                            item = gtk.MenuItem("Disable %s"  % screen.device_model_fullname)
                            item.connect("activate", self._disable, remote_device)
                            self.add_service_item(item)
                        
                        # Cycle screens
                        item = gtk.CheckMenuItem(_("Cycle screens automatically"))
                        item.set_active(g15gconf.get_bool_or_default(self.conf_client, "/apps/gnome15/%s/cycle_screens" % screen.device_uid, True))
                        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/%s/cycle_screens" % screen.device_uid, self._cycle_screens_option_changed))
                        item.connect("toggled", self._cycle_screens_changed, screen.device_uid)
                        self._append_item(item)
                        
                        # Alert message            
                        if screen.message:
                            self._append_item(gtk.MenuItem(screen.message))
                        
                        logger.debug("Adding items")
                        
                        
                        sorted_x = sorted(screen.items.iteritems(), key=operator.itemgetter(1))
                        for item_key, text in sorted_x:
                            logger.debug("Adding item %s = %s ", item_key, text)
                            item = gtk.MenuItem(text)
                            item.connect("activate", self._show_page, item_key)
                            self._append_item(item)
                    else:
                        # Enable
                        if len(devices) > 1:
                            item = gtk.MenuItem(_("Enable %s") % remote_device.GetModelFullName())
                            item.connect("activate", self._enable, remote_device)
                            self.add_service_item(item)
                    i += 1
            except Exception as e:
                logger.debug("Failed to find devices, service probably stopped.", exc_info = e)
                self.connected = False
                self.rebuild_desktop_component()
                
            self.devices = devices
        else:
            self.devices = []
            self.add_start_desktop_service()

        self.menu.show_all()
        self.check_attention()
        
    def add_start_desktop_service(self):
        item = gtk.MenuItem(_("Start Desktop Service"))
        item.connect("activate", self.start_desktop_service)
        self.add_service_item(item)
        
    def add_service_item(self, item):
        self._append_item(item)
        
    def initialise_desktop_component(self):
        
        self.last_items = []
        self.start_service_item = None
        self.attention_item = None
        self.notify_handles = []
        
        # Indicator menu
        self.menu = gtk.Menu()
        self.create_component()
        self.menu.show_all()
        
    def create_component(self):
        raise Exception("Not implemented")
        
    def remove_attention_menu_item(self):              
        if self.attention_item != None:
            self.menu.remove(self.attention_item)
            self.attention_item.destroy()
            self.menu.show_all()
            self.attention_item = None
        
    def options_changed(self):
        self.check_attention()
        
    """
    Private
    """
        
    def _get_active_screen_object(self):        
        screen = list(self.screens.values())[self.screen_number]
        return self.session_bus.get_object('org.gnome15.Gnome15', screen.path)
                
    def _set_active_screen_number(self):
        self._close_notify_message()
        screen = list(self.screens.values())[self.screen_number]
        body = _("%s is now the active keyboard. Use mouse wheel up and down to cycle screens on this device") % screen.device_model_fullname
        self.notify_message = g15notify.notify(screen.device_model_fullname, body, "preferences-desktop-keyboard-shortcuts")
        
    def _close_notify_message(self):
        if self.notify_message is not None:
            try:
                self.notify_message.close()
            except Exception as e:
                logger.debug("Failed to close message.", exc_info = e)
            self.notify_message = None
       
    def _append_item(self, item, menu = None):
        self.last_items.append(item)
        if menu is None:
            menu = self.menu
        menu.append(item)
        
    def _show_page(self,event, page_path):
        self.show_page(page_path)            
        
    def _cycle_screens_changed(self, widget, device_uid):
        self.conf_client.set_bool("/apps/gnome15/%s/cycle_screens" % device_uid, widget.get_active())
        
if __name__ == "__main__":
    print "g15-systemtray installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-systemtray"), is_autostart_application("g15-systemtray") )
    print "g15-desktop-service installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-desktop-service"), is_autostart_application("g15-desktop-service") )
    print "g15-indicator installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-indicator"), is_autostart_application("g15-indicator") )
    print "dropbox installed = %s, enabled = %s" % ( is_desktop_application_installed("dropbox"), is_autostart_application("dropbox") )
    print "xdropbox installed = %s, enabled = %s" % ( is_desktop_application_installed("xdropbox"), is_autostart_application("xdropbox") )
    print "nepomukserver installed = %s, enabled = %s" % ( is_desktop_application_installed("nepomukserver"), is_autostart_application("nepomukserver") )
    set_autostart_application("g15-indicator", False)
    print "g15-indicator installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-indicator"), is_autostart_application("g15-indicator") )
    set_autostart_application("g15-indicator", True)
    print "g15-indicator installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-indicator"), is_autostart_application("g15-indicator") )
