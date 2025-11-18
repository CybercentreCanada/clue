import useAppUser from 'commons/components/app/hooks/useAppUser';
import UserPageWrapper from 'components/elements/display/UserPageWrapper';
// import useMyLocalStorage from "components/hooks/useMyLocalStorage";
import type { ClueUser } from 'models/entities/ClueUser';
import type { FC } from 'react';
// import { StorageKey } from "utils/constants";
import LocalSection from './LocalSection';

const Settings: FC = () => {
  const { user: currentUser /*setUser*/ } = useAppUser<ClueUser>();

  // const { get } = useMyLocalStorage();

  // const isOAuth = useMemo(
  //   () => get<string>(StorageKey.APP_TOKEN)?.includes("."),
  //   [get]
  // );

  // const currentUserWrapper = useCallback(
  //   (fn: (user: ClueUser, newValue: unknown) => Promise<ClueUser>) => {
  //     return async (value: unknown) => setUser(await fn(currentUser, value));
  //   },
  //   [currentUser, setUser]
  // );

  return (
    <UserPageWrapper user={currentUser}>
      {/* <ProfileSection
        user={currentUser}
        editName={!isOAuth && currentUserWrapper(editName)}
        addRole={currentUser.is_admin && !isOAuth && currentUserWrapper(addRole)}
        removeRole={currentUser.is_admin && !isOAuth && currentUserWrapper(removeRole)}
        viewGroups={viewGroups}
      />
      <SecuritySection
        user={currentUser}
        editPassword={editPassword}
        addApiKey={addApiKey}
        removeApiKey={currentUserWrapper(removeApiKey)}
        editQuota={currentUser.is_admin && currentUserWrapper(editQuota)}
      /> */}
      <LocalSection />
    </UserPageWrapper>
  );
};

export default Settings;
