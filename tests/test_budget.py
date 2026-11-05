from test_workflows import WorkflowCase
import concurrent.futures

class BudgetChanges(WorkflowCase):
 def test_adjust_clear_and_validation(self):
  cookie=self.account();self.event(cookie)
  def change(operation,amount=0):return self.req('budget/adjust',{'operation':operation,'amount':amount},cookie)
  self.assertEqual(change('add',25.55)[1]['budget'],1000025.55)
  self.assertEqual(change('remove',25.55)[1]['budget'],1000000)
  for operation,value in [('remove',1000001),('add',0),('add',-1),('add',True),('add','nan'),('add',10000000001),('invalid',1)]:
   self.assertEqual(change(operation,value)[0],400)
  self.assertEqual(change('clear')[1]['budget'],0)
  self.assertEqual(change('add',1)[1]['budget'],1)
  self.assertEqual(len([a for a in self.req('audit',cookie=cookie)[1]['audit'] if a['action'].startswith('Budget ')]),4)
 def test_concurrent_updates_are_atomic_and_scoped(self):
  cookie=self.account();self.event(cookie)
  other=self.account('9888888801');self.event(other)
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
   results=list(pool.map(lambda _:self.req('budget/adjust',{'operation':'add','amount':10},cookie)[0],range(8)))
  self.assertEqual(results,[200]*8)
  self.assertEqual(self.req('state',cookie=cookie)[1]['event'][0]['budget'],1000080)
  self.assertEqual(self.req('state',cookie=other)[1]['event'][0]['budget'],1000000)
 def test_roles_cannot_change_budget(self):
  cookie=self.req('auth/demo',{'role':'Finance Team'})[2]
  self.assertEqual(self.req('budget/adjust',{'operation':'clear'},cookie)[0],403)
  self.assertEqual(self.req('budget/adjust',{'operation':'clear'})[0],401)
