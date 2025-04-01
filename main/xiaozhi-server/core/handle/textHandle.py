from config.logger import setup_logging
import json
from core.handle.abortHandle import handleAbortMessage
from core.handle.helloHandle import handleHelloMessage
from core.utils.util import remove_punctuation_and_length
from core.handle.receiveAudioHandle import startToChat, handleAudioMessage
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.iotHandle import handleIotDescriptors, handleIotStatus
from core.utils.nfc_card_manager import NFCCardManager

TAG = __name__
logger = setup_logging()


async def handleTextMessage(conn, message):
    """处理文本消息"""
    logger.bind(tag=TAG).info(f"收到文本消息：{message}")
    try:
        msg_json = json.loads(message)
        if isinstance(msg_json, int):
            await conn.websocket.send(message)
            return
        if msg_json["type"] == "nfc_card_detected":
            message = await getNFCCardMessage(conn, message)
            logger.bind(tag=TAG).info(f"type为nfc_card_detected处理后的消息：{message}")

        if msg_json["type"] == "hello":
            await handleHelloMessage(conn)
        elif msg_json["type"] == "abort":
            await handleAbortMessage(conn)
        elif msg_json["type"] == "listen":
            if "mode" in msg_json:
                conn.client_listen_mode = msg_json["mode"]
                logger.bind(tag=TAG).debug(f"客户端拾音模式：{conn.client_listen_mode}")
            if msg_json["state"] == "start":
                conn.client_have_voice = True
                conn.client_voice_stop = False
            elif msg_json["state"] == "stop":
                conn.client_have_voice = True
                conn.client_voice_stop = True
                if len(conn.asr_audio) > 0:
                    await handleAudioMessage(conn, b'')
            elif msg_json["state"] == "detect":
                conn.asr_server_receive = False
                conn.client_have_voice = False
                conn.asr_audio.clear()
                if "text" in msg_json:
                    text = msg_json["text"]
                    _, text = remove_punctuation_and_length(text)

                    # 识别是否是唤醒词
                    is_wakeup_words = text in conn.config.get("wakeup_words")
                    # 是否开启唤醒词回复
                    enable_greeting = conn.config.get("enable_greeting", True)

                    if is_wakeup_words and not enable_greeting:
                        # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                        await send_stt_message(conn, text)
                        await send_tts_message(conn, "stop", None)
                    else:
                        # 否则需要LLM对文字内容进行答复
                        await startToChat(conn, text)
        elif msg_json["type"] == "iot":
            if "descriptors" in msg_json:
                await handleIotDescriptors(conn, msg_json["descriptors"])
            if "states" in msg_json:
                await handleIotStatus(conn, msg_json["states"])
    except json.JSONDecodeError:
        await conn.websocket.send(message)

async def getNFCCardMessage(connection_handler, message_text):
    
    """处理NFC卡片检测消息"""
    logger = setup_logging()
    logger.bind(tag=TAG).info(f"接收到NFC卡片消息: {message_text}")
    
    try:
        # 直接使用json库解析，避免中间处理
        try:
            json_data = json.loads(message_text)
            logger.bind(tag=TAG).info(f"解析后的JSON数据: {json_data}")
        except json.JSONDecodeError as e:
            logger.bind(tag=TAG).error(f"JSON解析错误: {str(e)}")
            return {"type":"listen","mode":"manual","state":"detect","text":"我的卡片贴上来没识别到，请安慰安慰我啦"}
            
        # 验证必要字段
        if not isinstance(json_data, dict) or json_data.get("type") != "nfc_card_detected" or not json_data.get("card_id"):
            logger.bind(tag=TAG).error(f"缺少必要字段: {json_data}")
            return {"type":"listen","mode":"manual","state":"detect","text":"我的卡片贴上来没识别到必要字段，请安慰安慰我啦"}

        # 获取卡片ID
        card_id = json_data["card_id"]
        logger.bind(tag=TAG).info(f"检测到NFC卡片ID: {card_id}")
        
        # 查询卡片信息
        nfc_manager = NFCCardManager(connection_handler.config.get("log", {}).get("data_dir", "data"))
        card_info = nfc_manager.get_card_info(card_id)
        
        if not card_info:
            logger.bind(tag=TAG).warning(f"未找到卡片ID: {card_id}的信息")
            return {"type":"listen","mode":"manual","state":"detect","text":"我的卡片贴上来，没查到对应的信息，请安慰安慰我啦"}
        
        # 通知前端正在处理卡片
        await send_stt_message(connection_handler, f"识别到{card_info['card_name']}")
        return {"type":"listen","mode":"manual","state":"detect","text": f"{card_info['prompt']}"}
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理NFC卡片消息出错: {str(e)}")
        return {"type":"listen","mode":"manual","state":"detect","text": "我的卡片贴上来，报错了，请安慰安慰我啦"}