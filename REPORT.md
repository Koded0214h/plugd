Hey guys, these are some of the things I’ve noticed while testing. If anything already has logic behind it, just explain it to me. If not, we can tighten it up. We’re close, just want the core flow to feel clean before we go live.
	•	Service listing fields
	•	The location part is good, it being compulsory makes sense because it helps with search and matching.
	•	For the address, I think it should stay optional, and we add a small note under it saying something like “only enter your address if you have a fixed location to help clients find you”.
	•	The reason is it clears up confusion between fixed, mobile, and remote providers. Someone mobile shouldn’t feel forced to put an address.
	•	The remote or online switch is already done, which is good, that solves that side properly.
	•	Featured images
	•	This one matters a lot from a user perspective. Right now, if someone is booking directly from a service, they need to actually see what they’re booking.
	•	First image being the business logo makes sense for identity. After that, the rest should be service specific images.
	•	For example, if it’s hair, they should see actual work done. Without that, users are basically guessing, and that affects trust and conversion.
	•	Booking rules
	•	I noticed with manual approval, it shows as reserved, but there’s no actual option on the provider dashboard to approve or reject it.
	•	So the flow kind of stops there. The provider sees it, but can’t act on it.
	•	Ideally, there should be clear approve and decline actions so the provider can control bookings properly.
	•	Per day bookings
	•	For per day, the time isn’t that important. It can still be there, but it’s not really a core factor.
	•	What matters more is how many days the provider is available and how many days the customer selects.
	•	So it’s more about availability across days rather than specific hours.
	•	Booking limits
	•	I noticed that even when a provider sets limited hourly slots, a customer can still select more than what was intended.
	•	That can lead to overbooking, which will cause issues later.
	•	It would be better if bookings are strictly tied to the actual slots or limits the provider sets.
	•	Dashboard and routing
	•	Some parts of the dashboard feel unfinished in terms of interaction.
	•	For example, “awaiting payment” shows, but there’s nothing to click into or act on, so it just sits there.
	•	Also, the “sign in with Google” button is there but not working. When users click something and it doesn’t respond, it creates friction straight away.
	•	Another thing, when someone tries to book and is asked to create an account, that part works, but after they sign up, it doesn’t take them back to where they left off.
	•	So they have to restart the process, which can easily make people drop off.
	•	Stripe onboarding
	•	After completing Stripe setup, it’s meant to redirect back and confirm everything is done.
	•	Right now it goes to a “page not found”, and when you return manually, it still shows as if setup isn’t complete.
	•	So the status isn’t syncing properly, which can confuse providers.
	•	Reviews
	•	I haven’t fully confirmed this yet, but from what I’ve seen, the review system isn’t clearly available from the customer side.
	•	Just need clarity on whether it’s done or still pending.
	•	Hub
	•	I haven’t tested the hub fully yet, so I need a clear explanation of how it’s meant to work before I can give proper feedback.
	•	From a logic standpoint though, I think hubs should only have two pricing options.
	•	Either request a quote or fixed price.
	•	Since it’s multiple providers bundled together, per hour or per day doesn’t really fit that model.
	•	Service page layout
	•	This links back to images. If a user is booking directly from a service, they still need to see what that service looks like.
	•	It can’t just be pick a date and book.
	•	People decide based on visuals, especially for things like hair, design, cleaning, anything practical.
	•	Without that, it reduces confidence and makes the platform feel incomplete.
	•	Performance
	•	Loading is a bit slow right now.
	•	I understand it’s not live yet, so this might improve, but just something to keep an eye on.
	•	Codes system
	•	I’ve seen it appear on the provider side, which is a good sign.
	•	I haven’t tested it fully from the customer side yet, so I’ll check that next.
	•	Emails
	•	I think once the site is live, email flows should be the next focus.
	•	Things like confirmations, updates, and notifications will matter a lot for overall experience.

Overall, we’re in a good place. It’s mostly about tightening the core journeys so nothing feels broken or confusing. Once that foundation is clean, we can keep building on top of it.