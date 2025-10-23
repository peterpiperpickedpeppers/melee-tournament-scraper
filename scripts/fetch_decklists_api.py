#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : `date +%Y-%m-%d %H:%M:%S`
# @Author  : peterpiperpickedpeppers
# @Link    : https://github.com/peterpiperpickedpeppers


import requests
import json
import re
from pprint import pprint
from typing import Any, List, Dict
from bs4 import BeautifulSoup
import csv

URL = "https://melee.gg/Decklist/GetTournamentViewData/ae0cbfcc-2015-474f-9b7a-b3790026fef8"


def fetch_and_show(url: str = URL, save_file: str = "decklists_pretty.json") -> List[Any]:
	"""Fetch URL, parse JSON, pretty-print it, extract a list of items, and save pretty JSON to a file.

	Returns a Python list of items (if the top-level JSON is a list, that's returned; if it's a dict,
	the first list-valued key's value is returned; otherwise the dict is wrapped into a single-item list).
	"""
	try:
		r = requests.get(url, timeout=20)
		r.raise_for_status()
	except requests.RequestException as exc:
		print(f"HTTP error when fetching {url}: {exc}")
		raise

	try:
		data = r.json()
	except ValueError as exc:
		print("Response did not contain valid JSON:")
		print(r.text[:1000])  # show a bit of the raw response
		raise

	# Pretty print to console (careful with very large payloads)
	try:
		print("=== Pretty JSON ===")
		print(json.dumps(data, indent=2, ensure_ascii=False))
	except Exception:
		# fallback to pprint for non-serializable objects
		pprint(data)

	# Extract list of items
	if isinstance(data, list):
		items = data
	elif isinstance(data, dict):
		list_candidates = {k: v for k, v in data.items() if isinstance(v, list)}
		if list_candidates:
			first_key = next(iter(list_candidates))
			items = data[first_key]
		else:
			items = [data]
	else:
		items = [data]

	# Save pretty JSON to file
	try:
		with open(save_file, "w", encoding="utf-8") as fh:
			json.dump(data, fh, ensure_ascii=False, indent=2)
		print(f"Saved pretty JSON to {save_file}")
	except Exception as exc:
		print(f"Failed to save JSON to {save_file}: {exc}")

	return items


if __name__ == "__main__":
	items = fetch_and_show()
	print(f"\nExtracted {len(items)} items. Showing up to 5 items:")
	for i, it in enumerate(items[:5]):
		print(f"Item {i}:")
		pprint(it)

	# Try to parse inner JSON string if present (many responses embed a JSON string in 'Json')
	try:
		top = json.load(open("decklists_pretty.json", encoding="utf-8"))
	except Exception:
		top = None

	if top and isinstance(top, dict) and "Json" in top:
		try:
			inner = json.loads(top["Json"])
		except Exception:
			inner = None

		if inner and isinstance(inner, dict):
			# look for Standings -> list of players with DecklistGuid
			standings = inner.get("Standings") or []
			deck_guids = []
			for s in standings:
				guid = s.get("DecklistGuid")
				name = s.get("PlayerName") or s.get("PlayerUsername")
				if guid:
					deck_guids.append((guid, name))

			print(f"Found {len(deck_guids)} deck GUIDs to fetch details for.")

			session = requests.Session()

			def parse_card_lines(text: str) -> List[Dict[str, Any]]:
				"""Parse lines like '4 Lightning Bolt' and detect sideboard blocks.

				Returns list of dicts: {name, qty:int, zone:'main'|'side'}
				"""
				lines = [l.strip() for l in text.splitlines()]
				cards: List[Dict[str, Any]] = []
				zone = "main"
				for ln in lines:
					if not ln:
						continue
					# detect sideboard header
					if re.search(r"^sideboard[:\s]*$", ln, flags=re.I):
						zone = "side"
						continue
					m = re.match(r"^(\d+)\s+[×xX]?\s*(.+)$", ln)
					if m:
						qty = int(m.group(1))
						card = m.group(2).strip()
						cards.append({"name": card, "qty": qty, "zone": zone})
						continue
						# lines like 'Card Name — 2' or 'Card Name x2' or '2 Card Name'
						m4 = re.match(r"^(.+?)\s+[—-]\s*(\d+)$", ln)
						if m4:
							card = m4.group(1).strip()
							qty = int(m4.group(2))
							cards.append({"name": card, "qty": qty, "zone": zone})
							continue
					# fallback: lines like '2x Card Name' or 'Card Name x2' handled above partially
					m2 = re.match(r"^(\d+)x\s+(.+)$", ln, flags=re.I)
					if m2:
						qty = int(m2.group(1))
						card = m2.group(2).strip()
						cards.append({"name": card, "qty": qty, "zone": zone})
						continue
					# try trailing quantity
					m3 = re.match(r"^(.+?)\s+[×xX]\s*(\d+)$", ln)
					if m3:
						card = m3.group(1).strip()
						qty = int(m3.group(2))
						cards.append({"name": card, "qty": qty, "zone": zone})
						continue
					# otherwise ignore
				return cards

			def fetch_deck_by_guid(sess: requests.Session, guid: str) -> List[Dict[str, Any]]:
				"""Try multiple endpoints to fetch decklist data; return card dicts."""
				tried = []
				candidates = [
					f"https://melee.gg/Decklist/GetDecklist/{guid}",
					f"https://melee.gg/Decklist/Get/{guid}",
					f"https://melee.gg/Decklist/GetDecklist?decklistGuid={guid}",
					f"https://melee.gg/Decklist/View/{guid}",
					f"https://melee.gg/Decklist/Details/{guid}",
				]
				for u in candidates:
					try:
						r = sess.get(u, timeout=20)
					except Exception:
						continue
					tried.append((u, r.status_code, r.headers.get("Content-Type", "")))
					if r.status_code != 200:
						continue
					ct = r.headers.get("Content-Type", "")
					if "application/json" in ct or r.text.strip().startswith("{"):
						try:
							j = r.json()
						except Exception:
							# sometimes JSON is returned as a string inside a property
							try:
								j = json.loads(r.text)
							except Exception:
								continue
						# possible shapes: {'Mainboard':[{'Name','Quantity'}], 'Sideboard':[...]}
						cards = []
						if isinstance(j, dict):
							# common keys
							if "Mainboard" in j or "Sideboard" in j:
								main = j.get("Mainboard", []) or j.get("Main", []) or []
								side = j.get("Sideboard", []) or j.get("Side", []) or []
								for it in main:
									# handle both dicts and strings
									if isinstance(it, dict):
										name = it.get("Name") or it.get("CardName") or it.get("name")
										qty = it.get("Quantity") or it.get("Qty") or it.get("quantity") or 1
									else:
										# maybe '4 Lightning Bolt'
										parsed = parse_card_lines(str(it))
										if parsed:
											for p in parsed:
												cards.append({**p})
											continue
										name = str(it)
										qty = 1
									if name:
										cards.append({"name": name, "qty": int(qty), "zone": "main"})
								for it in side:
									if isinstance(it, dict):
										name = it.get("Name") or it.get("CardName") or it.get("name")
										qty = it.get("Quantity") or it.get("Qty") or it.get("quantity") or 1
									else:
										parsed = parse_card_lines(str(it))
										if parsed:
											for p in parsed:
												p["zone"] = "side"
												cards.append({**p})
											continue
										name = str(it)
										qty = 1
									if name:
										cards.append({"name": name, "qty": int(qty), "zone": "side"})
								if cards:
									return cards
							# sometimes decklist returned as flat text under 'Decklist' or 'Json'
							for k in ("Decklist", "Json", "Html"):
								if k in j and isinstance(j[k], str):
									txt = j[k]
									parsed = parse_card_lines(txt)
									if parsed:
										return parsed
						# fallback: no cards found in JSON response
					# if HTML, try to parse lines
					if "text/html" in ct or True:
						soup = BeautifulSoup(r.text, "html.parser")
						# robustly find divs where class attribute contains 'decklist-container'
						deck_containers = []
						for tag in soup.find_all('div'):
							classes = tag.get('class') or []
							if any('decklist-container' == c or 'decklist-container' in c for c in classes):
								deck_containers.append(tag)

						candidates_sel = []
						if deck_containers:
							for dc in deck_containers:
								# structured extraction: first look for ul/li pairs
								found = False
								# if li elements exist, parse them with quantity spans if present
								uls = dc.find_all('ul')
								if uls:
									for ul in uls:
										# extract li entries, honoring spans for qty/name
										txt_lines = []
										for li in ul.find_all('li'):
											# try structured qty span
											qty = None
											name = None
											# common patterns: <li><span class="qty">4</span><span class="name">Card</span></li>
											spans = li.find_all('span')
											if spans and len(spans) >= 2:
												# try find numeric span
												for sp in spans:
													scls = ' '.join(sp.get('class') or [])
													if re.search(r'qty|count|quantity', scls, flags=re.I) or re.match(r'^[0-9]+$', sp.get_text(strip=True)):
														qty = sp.get_text(strip=True)
													else:
														# treat as name if not numeric
														if not name:
															name = sp.get_text(strip=True)
											if not name:
												name = li.get_text(separator=' ').strip()
											if qty:
												txt_lines.append(f"{qty} {name}")
											else:
												txt_lines.append(name)
										candidates_sel.append('\n'.join(txt_lines))
									found = True
								if found:
									continue

								# headings + sibling lists
								for h in dc.find_all(re.compile('^h[1-6]$')):
									nxt = h.find_next_sibling()
									if nxt and nxt.name == 'ul':
										candidates_sel.append(nxt.get_text(separator='\n'))
										found = True
								if found:
									continue

								# column heuristics
								cols = dc.find_all(class_=re.compile('col|column'))
								if cols:
									for col in cols:
										candidates_sel.append(col.get_text(separator='\n'))
									continue

								# fallback to dc text
								candidates_sel.append(dc.get_text(separator="\n"))
						else:
							# common fallback classes/ids
							for sel in [".decklist", ".decklist-body", ".decklist-main", ".decklist-cards", "#decklist"]:
								el = soup.select_one(sel)
								if el:
									candidates_sel.append(el.get_text(separator="\n"))
						# also look for headings then ul/li pairs
						if not candidates_sel:
							# find headings like 'Mainboard' then following ul
							for heading in soup.find_all(re.compile('^h[1-6]$')):
								if heading and re.search(r"decklist|mainboard|sideboard|main|side", heading.get_text(), flags=re.I):
									nxt = heading.find_next_sibling()
									if nxt:
										candidates_sel.append(nxt.get_text(separator="\n"))
						# fallback: whole body text
						if not candidates_sel:
							candidates_sel.append(soup.get_text(separator="\n"))

						for txt in candidates_sel:
							parsed = parse_card_lines(txt)
							if parsed:
								return parsed

				# nothing found
				# print debug of tried endpoints
				print(f"Tried endpoints for {guid}: {tried}")
				return []

			all_card_rows: List[Dict[str, Any]] = []
			for guid, player in deck_guids:
				print(f"Fetching deck {guid} for player {player}")
				cards = fetch_deck_by_guid(session, guid)
				if not cards:
					print(f"No cards parsed for {guid}")
				for c in cards:
					all_card_rows.append({
						"player": player,
						"decklist_guid": guid,
						"card_name": c["name"],
						"qty": c["qty"],
						"zone": c.get("zone", "main"),
					})

			# save CSV
			if all_card_rows:
				csv_file = "deck_cards.csv"
				with open(csv_file, "w", newline="", encoding="utf-8") as fh:
					writer = csv.DictWriter(fh, fieldnames=["player", "decklist_guid", "card_name", "qty", "zone"])
					writer.writeheader()
					for r in all_card_rows:
						writer.writerow(r)
				print(f"Saved {len(all_card_rows)} card rows to {csv_file}")
			else:
				print("No card rows extracted from any decklist.")

