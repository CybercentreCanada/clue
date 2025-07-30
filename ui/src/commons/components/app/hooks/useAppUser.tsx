import { useContext } from 'react';
import { AppUser, AppUserService } from '../AppUserService';
import { AppUserContext } from '../providers/AppUserProvider';

export default function useAppUser<U extends AppUser>(): AppUserService<U> {
  return useContext(AppUserContext) as AppUserService<U>;
}
