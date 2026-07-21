flutter_file = r"d:\work\flutter_ai_talk\app\lib\ui\pangbao_ai_screen.dart"

with open(flutter_file, "r", encoding="utf-8") as f:
    content = f.read()

old_chat_item = """class _ChatItem {
  _ChatItem.user(this.question)
      : isUser = true,
        answer = null,
        thinking = null;

  _ChatItem.assistant()
      : isUser = false,
        question = null,
        thinking = '',
        answer = '';

  final bool isUser;
  final String? question;
  String? thinking;
  String? answer;
  var thinkingExpanded = false;
  var isError = false;
  String? errorMessage;
}"""

new_chat_item = """class _ChatItem {
  _ChatItem.user(this.question)
      : isUser = true,
        answer = null,
        thinking = null;

  _ChatItem.assistant()
      : isUser = false,
        question = null,
        thinking = '',
        answer = '';

  final bool isUser;
  final String? question;
  String? thinking;
  String? answer;
  String? answerId;
  var thinkingExpanded = false;
  var isError = false;
  String? errorMessage;
  var feedbackGiven = false;
}"""

content = content.replace(old_chat_item, new_chat_item)

old_answer_done = """        case 'answer_done':
          _activeAssistant!.thinkingExpanded = false;
          _activeAssistant!.thinking = frame['thinking'] as String? ?? _activeAssistant!.thinking;
          _activeAssistant!.answer = frame['answer'] as String? ?? _activeAssistant!.answer;
          _activeTurnId = null;
          _activeAssistant = null;
          ref.invalidate(voiceAiQuotaProvider);
          unawaited(_persistSessionStore());
          break;"""

new_answer_done = """        case 'answer_done':
          _activeAssistant!.thinkingExpanded = false;
          _activeAssistant!.thinking = frame['thinking'] as String? ?? _activeAssistant!.thinking;
          _activeAssistant!.answer = frame['answer'] as String? ?? _activeAssistant!.answer;
          _activeAssistant!.answerId = frame['answerId'] as String? ?? '';
          _activeTurnId = null;
          _activeAssistant = null;
          ref.invalidate(voiceAiQuotaProvider);
          unawaited(_persistSessionStore());
          break;"""

content = content.replace(old_answer_done, new_answer_done)

old_build_item_end = """         if (!item.isError && (item.answer ?? '').isNotEmpty)
           Padding(
             padding: const EdgeInsets.only(bottom: 16),
             child: Text(
               '本回答仅供参考，不能替代医生诊断',
               style: TextStyle(fontSize: 11, color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.45)),
             ),
           ),
       ],
     );
   }
 }"""

new_build_item_end = """         if (!item.isError && (item.answer ?? '').isNotEmpty)
           Padding(
             padding: const EdgeInsets.only(bottom: 16),
             child: Text(
               '本回答仅供参考，不能替代医生诊断',
               style: TextStyle(fontSize: 11, color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.45)),
             ),
           ),
         if (!item.isError && !item.feedbackGiven && (item.answerId ?? '').isNotEmpty)
           Padding(
             padding: const EdgeInsets.only(bottom: 16),
             child: Row(
               children: [
                 Text(
                   '这个回答有用吗？',
                   style: TextStyle(fontSize: 13, color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6)),
                 ),
                 const SizedBox(width: 8),
                 IconButton(
                   icon: const Icon(Icons.thumb_up, size: 20),
                   onPressed: () => _submitFeedback(item, 1),
                   tooltip: '有用',
                 ),
                 IconButton(
                   icon: const Icon(Icons.thumb_down, size: 20),
                   onPressed: () => _submitFeedback(item, -1),
                   tooltip: '没用',
                 ),
               ],
             ),
           ),
       ],
     );
   }

   Future<void> _submitFeedback(_ChatItem item, int feedback) async {
     final answerId = item.answerId;
     if (answerId == null || answerId.isEmpty) return;
     setState(() => item.feedbackGiven = true);
     final dn = ref.read(deviceNoNotifierProvider).asData?.value;
     if (dn == null || dn.isEmpty) return;
     try {
       final client = HttpClient();
       final url = Uri.parse('${AppEnv.apiBaseUrl}/device/api/clinic/feedback');
       final request = await client.postUrl(url);
       request.headers.contentType = ContentType.json;
       request.write('{"answerId": "$answerId", "feedback": $feedback}');
       final response = await request.close();
       await response.drain();
       client.close();
     } catch (e) {
       AppDebugLog.pangbaoClinic('feedback submit failed: $e');
     }
   }
 }"""

content = content.replace(old_build_item_end, new_build_item_end)

if 'import \'dart:io\'' not in content:
    content = 'import \'dart:io\';\n\n' + content

with open(flutter_file, "w", encoding="utf-8") as f:
    f.write(content)

print("Flutter pangbao_ai_screen.dart updated successfully!")
