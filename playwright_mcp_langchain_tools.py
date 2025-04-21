import json
import re
import os
import sys
import time  # 時間計測用に追加
import operator
import datetime  # 日付時刻の処理に必要
import base64  # base64エンコードされた画像の処理に必要
from typing_extensions import TypedDict
from typing import Any, Callable, Dict, Iterable, List, Optional, TypedDict, Annotated
from mcp.types import ImageContent

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI  # OpenAIのインポートを追加
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage, ToolMessage

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from langchain_mcp_adapters.client import MultiServerMCPClient

google_api_key = os.getenv("GOOGLE_APIKEY")
openai_api_key = os.getenv("OPENAI_API_KEY")  # OpenAIのAPIキーを環境変数から取得

# スクリーンショット保存用のディレクトリを作成
SCREENSHOTS_DIR = "screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


# スクリーンショットを処理する関数
def process_screenshot(message):
    """
    ツールのレスポンスからスクリーンショットを抽出して保存する
    """
    # ツールメッセージを処理
    if isinstance(message, ToolMessage):
        try:
            # ツールメッセージから画像データを抽出
            content = message.artifact
            if content is not None:
                base64_data = content[0].data
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(SCREENSHOTS_DIR, f"screenshot_{timestamp}.png")
                
                with open(screenshot_path, "wb") as img_file:
                    img_file.write(base64.b64decode(base64_data))
                print(f"ツールからスクリーンショットを保存しました: {screenshot_path}")
                return True
        except Exception as e:
            print(f"ツールレスポンスからのスクリーンショット保存に失敗しました: {e}")
    return False

def create_graph(state: GraphState, tools, model_chain):
    def should_continue(state):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return END

    def call_model(state):
        messages = state["messages"]
        # 直前はtoolsのメッセージであるため、最後のメッセージを取得し、画像を保存する。
        last_message = messages[-1]
        bool = process_screenshot(last_message)


        # model_chain.invokeの実行時間を計測
        start_time = time.time()
        response = model_chain.invoke(messages)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"model_chain.invokeの実行時間: {execution_time:.2f}秒")

        return {"messages": [response]}


    tool_node = ToolNode(tools)
    
    workflow = StateGraph(state)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app

async def main(graph_config = {"configurable": {"thread_id": "12345"}}):
    # モデル設定の読み込み
    with open("mcp_config.json", "r") as f:
        mcp_config = json.load(f)
    
    # モデル設定の取得
    model_config = mcp_config.get("modelConfig", {})
    provider = model_config.get("provider", "google")  # デフォルトはGoogle
    
    # モデルプロバイダーに基づいてモデルを初期化
    if provider == "google":
        if not google_api_key:
            raise ValueError("GOOGLE_APIKEYが設定されていません")
        
        google_model_config = model_config.get("models", {}).get("google", {})
        model = ChatGoogleGenerativeAI(
            model=google_model_config.get("model", "gemini-2.0-flash"),
            google_api_key=google_api_key,
            temperature=google_model_config.get("temperature", 0.1),
        )
        print("Google Geminiモデルを使用します")
    elif provider == "openai":
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません")
        
        openai_model_config = model_config.get("models", {}).get("openai", {})
        model = ChatOpenAI(
            model=openai_model_config.get("model", "gpt-4.1-mini"),
            openai_api_key=openai_api_key,
            temperature=openai_model_config.get("temperature", 0.1),
        )
        print("OpenAIモデルを使用します")
    else:
        raise ValueError(f"未対応のプロバイダー: {provider}")


    # messageを作成する
    message = [
        SystemMessage(content= """
あなたは役にたつAIアシスタントです。日本語で回答し、考えた過程を結論より前に出力してください。
あなたは、「PlayWright」というブラウザを操作するtoolを利用することができます。適切に利用してユーザからの質問に回答してください。
ツールを利用する場合は、必ずツールから得られた情報のみを利用して回答してください。

まず、ユーザの質問からツールをどういう意図で何回利用しないといけないのかを判断し、必要なら複数回toolを利用して情報収集をしたのち、すべての情報が取得できたら、その情報を元に返答してください。

ブラウザ操作後は１回の操作後に必ずbrowser_take_screenshot toolを使用してスクリーンショットを取得してください。
    """),
        MessagesPlaceholder("messages"),
    ]

    # messageからプロンプトを作成
    prompt = ChatPromptTemplate.from_messages(message)

    async with MultiServerMCPClient(mcp_config["mcpServers"]) as mcp_client:
        tools = mcp_client.get_tools()

        model_with_tools = prompt | model.bind_tools(tools)

        graph = create_graph(
            GraphState,
            tools,
            model_with_tools
        )


        query = input("入力してください:exitで終了: ")

        if query.lower() in ["exit", "quit"]:
            print("終了します。")
            exit()

        input_query = [HumanMessage(
                [
                    {
                        "type": "text",
                        "text": f"{query}"
                    },
                ]
            )]

        response = await graph.ainvoke({"messages":input_query}, graph_config)

        # スクリーンショットを処理
        process_screenshot(response["messages"])

        # デバック用
        # print("response: ", response)

        # 最終的な回答
        print("=================================")
        print(response["messages"][-1].content)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

