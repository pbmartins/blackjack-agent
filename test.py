import card

def p_bust(player_hand, limit):
    all_cards = [card.Card(rank=r) for r in range(1, 14)]
    scenarios = [card.value(player_hand + [c]) for c in all_cards]
    print(scenarios)
    print([v for v in scenarios if limit(v)])
    return len([v for v in scenarios if limit(v)]) / len(scenarios)

player_hand = [card.Card(rank=1), card.Card(rank=6)]
dealer_hand = [card.Card(rank=7)]
print(card.value(player_hand))
print(p_bust(dealer_hand, lambda v: v > card.value(player_hand) and v < 22))
