import os
from unittest.mock import patch
from test_workflows import WorkflowCase
import help_assistant,providers

class HelpBox(WorkflowCase):
 def test_guide_auth_validation_and_privacy(self):
  with patch.dict(os.environ,{'OPENAI_API_KEY':''}):
   self.assertFalse(self.req('help/status')[1]['aiConfigured'])
   self.assertEqual(self.req('help',{'question':'photos'})[0],401)
   cookie=self.req('auth/demo',{'role':'Guest'})[2]
   status,data,_=self.req('help',{'question':'How do I add photos?'},cookie)
   self.assertEqual(status,200);self.assertEqual(data['mode'],'guide');self.assertIn('Add photos',data['answer'])
   self.assertIn('restricted',self.req('help',{'question':'budget'},cookie)[1]['answer'])
   for question in ['',None,'x'*1201]:self.assertEqual(self.req('help',{'question':question},cookie)[0],400)
   self.assertEqual(self.req('help',{'question':'photos'},cookie,{'X-CSRF-Token':'bad'})[0],403)
 def test_ai_contract_and_failure_fallback(self):
  with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key-not-real','OPENAI_MODEL':'test-model'}),patch('providers.request') as request:
   request.return_value={'output':[{'content':[{'type':'output_text','text':'Open Memories.'}]}]}
   result=help_assistant.answer('How do I upload?','Guest');self.assertEqual(result,{'answer':'Open Memories.','mode':'ai'})
   payload=request.call_args.args[1];self.assertFalse(payload['store']);self.assertEqual(payload['input'],'How do I upload?');self.assertNotIn('phone',payload)
   request.side_effect=providers.ProviderError('secret details')
   result=help_assistant.answer('photos','Guest');self.assertEqual(result['mode'],'guide');self.assertNotIn('secret details',str(result));self.assertIn('notice',result)
 def test_rate_limit(self):
  cookie=self.req('auth/demo',{'role':'Guest'})[2]
  with patch.dict(os.environ,{'OPENAI_API_KEY':''}):
   for _ in range(20):self.assertEqual(self.req('help',{'question':'photos'},cookie)[0],200)
   self.assertEqual(self.req('help',{'question':'photos'},cookie)[0],429)
