import { createContext, ReactNode } from 'react';
import { AppUser, AppUserService } from '../AppUserService';

type AppUserProviderProps<U extends AppUser> = {
  service: AppUserService<U>;
  children: ReactNode;
};

const AppUserServiceImpl = {
  user: null,
  setUser: () => null,
  isReady: () => false,
  validateProps: () => true
};

export const AppUserContext = createContext<AppUserService<AppUser>>(null);

export default function AppUserProvider<U extends AppUser>({
  service = AppUserServiceImpl,
  children
}: AppUserProviderProps<U>) {
  return <AppUserContext.Provider value={{ ...AppUserServiceImpl, ...service }}>{children}</AppUserContext.Provider>;
}
