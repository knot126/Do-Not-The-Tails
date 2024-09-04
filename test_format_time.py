def formatTime(t):
	seconds = t % 60
	minutes = (t // 60) % 60
	hours = (t // 60) // 60
	s = []
	
	if hours != 0:
		s.append(f"{hours} hour" + ("s" if hours != 1 else ""))
	
	if minutes != 0:
		s.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
	
	if seconds != 0:
		s.append(f"{seconds} second" + ("s" if seconds != 1 else ""))
	
	return " ".join(s)
