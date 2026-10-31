import { clerkConfigured } from '@/lib/server/clerk';
import { FormWorkbench } from '@/components/forms/form-workbench';
import { AccountWorkbench } from '@/components/forms/account-workbench';
export const dynamic = 'force-dynamic';
export default function FormPage() {
  return clerkConfigured() ? <AccountWorkbench /> : <FormWorkbench accountState="unconfigured" />;
}
