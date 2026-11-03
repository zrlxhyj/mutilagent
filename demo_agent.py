from tools.tavily_tools import search_web

response = search_web("请用一句话解释 Agent。")#回复是字符串类型
#print(response)
for item in response.get("results", []):#这里只能用results
    print(item.get("title"))